"""Interface locale : copies USB/dossiers et réception HTTPS vérifiée."""
import queue
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .engine import LocalSource, Options, Transfer, TransferError, OperationCancelled
from .network import RemoteSource, read_token
from .delta import DeltaSource
from .ui_feedback import outcome, error_action
from .invitation import read_invitation
from .installation_status import installation_notice
from .report_view import capture_result, render_report
from .viewport import ScrollPanel, initial_size


class App:
    def __init__(self, root):
        self.root = root
        root.title(f"UltraTransfert {__version__} · copie vérifiée")
        root.geometry(initial_size(root.winfo_screenwidth(), root.winfo_screenheight()))
        root.minsize(720, 400)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.running = False
        self.stop_requested = False
        self.invitation = None
        self.editable = []
        self.last_destination = None
        self.verified_destination = None
        self.report_data = None
        self.report_kind = None
        self.report_message = ''
        self.viewport = ScrollPanel(root)
        panel = self.viewport.panel
        ttk.Label(panel, text="UltraTransfert", font=("Segoe UI", 26, "bold")).pack(anchor="w")
        ttk.Label(panel, text="1. Choisir les dossiers   2. Copier   3. Vérifier le résultat").pack(anchor="w", pady=(0, 14))
        setup_button = ttk.Button(panel, text="Émettre en HTTPS…", command=self.open_share_setup)
        setup_button.pack(anchor="w", pady=(0, 8))
        self.editable.append((setup_button, "normal"))
        self.setup_window = None
        self.tabs = ttk.Notebook(panel)
        self.tabs.pack(fill="x")
        local, remote = ttk.Frame(self.tabs, padding=12), ttk.Frame(self.tabs, padding=12)
        self.tabs.add(local, text="Copier : ordinateur / USB / réseau / lecteur RDP")
        self.tabs.add(remote, text="Recevoir en HTTPS")
        self.local_source = self.path_field(local, "Dossier à copier", directory=True)
        ttk.Label(local, text="En session RDP : choisissez un lecteur redirigé autorisé dans Parcourir.\nLa redirection doit être activée ; ce mode utilise la copie de dossiers.", wraplength=600).pack(anchor="w", pady=8)
        invitation_controls = ttk.Frame(remote)
        invitation_controls.pack(fill="x")
        invitation_button = ttk.Button(invitation_controls, text="Ouvrir une invitation…", command=self.open_invitation)
        invitation_button.pack(side="left")
        manual_button = ttk.Button(invitation_controls, text="Configuration manuelle", command=self.use_manual)
        manual_button.pack(side="left", padx=8)
        self.editable.extend([(invitation_button, "normal"), (manual_button, "normal")])
        self.invitation_status = tk.StringVar(value="Ouvrez le fichier d'invitation reçu de l'émetteur de confiance.")
        ttk.Label(remote, textvariable=self.invitation_status, wraplength=600).pack(anchor="w", pady=8)
        self.manual = ttk.Frame(remote)
        self.remote_url = self.path_field(self.manual, "Adresse du serveur (https://ordinateur:8443)")
        self.remote_ca = self.path_field(self.manual, "Certificat de confiance (.pem)", directory=False)
        self.remote_token = self.path_field(self.manual, "Fichier contenant le jeton d'accès", directory=False)
        self.reference = self.path_field(self.manual, "Ancienne copie locale à réutiliser (facultatif, serveur --delta)", directory=True)
        self.compression = tk.BooleanVar(value=True)
        check = ttk.Checkbutton(remote, text="Autoriser la compression réseau", variable=self.compression)
        check.pack(anchor="w")
        self.editable.append((check, "normal"))
        self.predictive = tk.BooleanVar(value=False)
        experiment = ttk.Checkbutton(remote, text="Compression prédictive R2.2 / lecture R3.1 (essai, même mode chez l’émetteur)", variable=self.predictive)
        experiment.pack(anchor="w")
        self.editable.append((experiment, "normal"))
        self.destination = self.path_field(panel, "Dossier destination", directory=True)
        self.advanced = ttk.Frame(panel)
        self.advanced_visible = False
        self.advanced_button = ttk.Button(panel, text="Réglages avancés ▸", command=self.toggle_advanced)
        self.advanced_button.pack(anchor="w", pady=6)
        settings = self.advanced
        ttk.Label(settings, text="Transferts parallèles :").pack(side="left")
        self.workers = tk.StringVar(value="Auto")
        workers_box = ttk.Combobox(settings, textvariable=self.workers, values=("Auto", "1", "2", "4", "8"), state="readonly", width=8)
        workers_box.pack(side="left", padx=8)
        self.editable.append((workers_box, "readonly"))
        speed_row = ttk.Frame(panel)
        self.speed_row = speed_row
        ttk.Label(speed_row, text="Vitesse maximale de copie (Mo/s) :").pack(side="left")
        self.speed_limit = tk.StringVar(value="Sans limite")
        speed_box = ttk.Combobox(speed_row, textvariable=self.speed_limit, values=("Sans limite", "1", "5", "10", "25", "50"), state="readonly", width=12)
        speed_box.pack(side="left", padx=8)
        self.editable.append((speed_box, "readonly"))
        self.status = tk.StringVar(value=installation_notice() or "Choisissez une destination vide ou le dossier d'un transfert à reprendre.")
        self.bar = ttk.Progressbar(panel, maximum=100)
        self.bar.pack(fill="x", pady=(12, 8))
        ttk.Label(panel, textvariable=self.status, wraplength=600).pack(anchor="w")
        controls = ttk.Frame(panel)
        controls.pack(fill="x", pady=12)
        self.begin = ttk.Button(controls, text="Copier / reprendre", command=self.start)
        self.begin.pack(side="left")
        self.stop = ttk.Button(controls, text="Interrompre", command=self.request_stop, state="disabled")
        self.stop.pack(side="left", padx=8)
        self.report = ttk.Button(controls, text="Voir le bilan", command=self.show_report, state="disabled")
        self.report.pack(side="left")
        self.result_button = ttk.Button(controls, text="Ouvrir la destination", command=self.open_destination, state="disabled")
        self.result_button.pack(side="left", padx=(8, 0))
        ttk.Label(panel, text="Contrôle SHA-256 systématique. Aucun fichier différent n'est écrasé.\nLes ACL, flux NTFS alternatifs et attributs étendus ne sont pas copiés.", wraplength=600).pack(anchor="w", pady=8)
        footer = ttk.Frame(panel)
        footer.pack(fill='x', pady=(4, 8))
        ttk.Label(footer, text='Logiciel libre · licence MIT').pack(side='left')
        ttk.Button(footer, text='Soutenir le projet (Bitcoin)...', command=self.open_donations).pack(side='right')
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)

    def open_donations(self):
        from .donations import show_donations
        return show_donations(self.root)

    def open_share_setup(self):
        if self.running:
            return
        if self.setup_window is not None and self.setup_window.window.winfo_exists():
            self.setup_window.window.lift()
            return
        from .share_setup_gui import SetupDialog
        self.setup_window = SetupDialog(self.root)

    def path_field(self, parent, title, directory=None):
        ttk.Label(parent, text=title).pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(3, 4))
        value = tk.StringVar()
        entry = ttk.Entry(row, textvariable=value)
        entry.pack(side="left", fill="x", expand=True)
        self.editable.append((entry, "normal"))
        if directory is not None:
            picker = filedialog.askdirectory if directory else filedialog.askopenfilename
            button = ttk.Button(row, text="Parcourir", command=lambda: value.set(picker() or value.get()))
            button.pack(side="left", padx=(8, 0))
            self.editable.append((button, "normal"))
        return value

    def open_invitation(self):
        if self.running:
            return
        path = filedialog.askopenfilename(title="Invitation UltraTransfert", filetypes=[("Invitation", "*.utconnect"), ("Tous les fichiers", "*")])
        if not path:
            return
        try:
            invitation = read_invitation(path)
        except (OSError, ValueError, TransferError) as exc:
            messagebox.showerror("Invitation invalide", str(exc))
            return
        fingerprint = " ".join(invitation.certificate_sha256[i:i+8] for i in range(0, 64, 8))
        if not messagebox.askyesno("Vérifier l'émetteur", f"Adresse : {invitation.url}\nEmpreinte SHA-256 du certificat :\n{fingerprint}\n\nComparez cette empreinte avec l'émetteur par un autre canal de confiance. Le fichier contient un accès secret aux données partagées.\n\nAvez-vous vérifié cette adresse et cette empreinte ?"):
            return
        self.invitation = invitation
        self.manual.pack_forget()
        self.reference.set("")
        self.invitation_status.set("Invitation confirmée : "+invitation.url+". Choisissez la destination puis Copier / reprendre.")

    def use_manual(self):
        if self.running:
            return
        self.invitation = None
        self.manual.pack(fill="x")
        self.invitation_status.set("Mode manuel : adresse, certificat public et fichier d'accès requis.")

    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced.pack(fill="x", after=self.advanced_button)
            self.speed_row.pack(fill="x", after=self.advanced)
        else:
            self.advanced.pack_forget()
            self.speed_row.pack_forget()
        self.advanced_button.configure(text="Réglages avancés ▾" if self.advanced_visible else "Réglages avancés ▸")

    def set_running(self, running):
        self.running = running
        if running:
            self.active_tab = self.tabs.select()
        for widget, idle_state in self.editable:
            widget.configure(state="disabled" if running else idle_state)
        for index in range(2):
            self.tabs.tab(index, state="disabled" if running else "normal")
        if not running:
            self.tabs.select(self.active_tab)
        self.begin.configure(state="disabled" if running else "normal")
        self.stop.configure(state="normal" if running else "disabled")

    def request_stop(self):
        if not self.running:
            return
        self.stop_requested = True
        self.cancel.set()
        self.stop.configure(state="disabled")
        self.status.set("Arrêt en cours… Les données partielles seront conservées. Attendez le résultat.")

    def start(self):
        if self.running:
            return
        remote = self.tabs.index(self.tabs.select()) == 1
        source, destination = self.local_source.get(), self.destination.get()
        url, ca, token = self.remote_url.get(), self.remote_ca.get(), self.remote_token.get()
        reference = self.reference.get()
        invitation = getattr(self, "invitation", None) if remote else None
        if not destination or (remote and invitation is None and not all((url, ca, token))) or (not remote and not source):
            messagebox.showerror("Champs manquants", "Choisissez le dossier à copier et sa destination." if not remote else "Ouvrez une invitation, ou choisissez Configuration manuelle pour renseigner l’adresse, le certificat et le fichier d’accès. Choisissez aussi une destination.")
            return
        workers = 0 if self.workers.get() == "Auto" else int(self.workers.get())
        limit = 0 if self.speed_limit.get() == "Sans limite" else float(self.speed_limit.get())*1e6
        compression = "auto" if self.compression.get() else "none"
        if getattr(self, "predictive", None) is not None and self.predictive.get():
            compression = "predictive"
        self.stop_requested = False
        self.cancel.clear()
        self.set_running(True)
        self.report.configure(state="disabled")
        self.result_button.configure(state="disabled")
        self.verified_destination = None
        self.last_destination = destination
        self.report_data = None
        self.report_kind = None
        self.report_message = ''
        self.bar.stop()
        self.bar.configure(mode="indeterminate")
        self.bar.start(12)
        self.status.set("Inventaire de la source en cours…")
        started, last = time.monotonic(), [0.0]

        def progress(n, total):
            now = time.monotonic()
            if now-last[0] >= 0.15:
                last[0] = now
                self.events.put(("progress", n, total, now-started))

        def work():
            try:
                origin = (invitation.remote_source(compression) if invitation is not None else
                          RemoteSource(url, read_token(token), ca, compression)) if remote else LocalSource(source, cancel=self.cancel)
                if remote and reference:
                    origin = DeltaSource(origin, reference, self.cancel,
                                         lambda text: self.events.put(("phase", text)))
                result = Transfer(origin, destination, Options(workers=workers, max_bytes_per_second=limit), progress, self.cancel,
                                  lambda text: self.events.put(("phase", text))).run()
                self.events.put(("report_data", capture_result(result)))
                kind = outcome(result.errors, self.stop_requested)
                if kind == "stopped":
                    self.events.put(("stopped", "Copie interrompue. Cliquez sur Reprendre en gardant les mêmes dossiers. Les données réutilisées seront vérifiées."))
                    return
                if result.errors:
                    raise RuntimeError("\n".join(result.errors))
                details = ""
                if isinstance(origin, DeltaSource):
                    stats = origin.statistics()
                    details = f"\nDelta : {stats['reused_payload_bytes']/1e6:.2f} Mo réutilisés · {stats['downloaded_payload_bytes']/1e6:.2f} Mo téléchargés (hors protocole)"
                self.events.put(("done", f"Copie terminée et vérifiée : {result.files} fichiers · {result.bytes/1e9:.3f} Go · {result.seconds:.2f} s (hors inventaire/indexation)"+details))
            except OperationCancelled as exc:
                if self.stop_requested:
                    self.events.put(("stopped", "Inventaire interrompu. Aucune copie annoncée terminée. Cliquez sur Reprendre avec les mêmes dossiers ; les données seront vérifiées."))
                else:
                    self.events.put(("error", str(exc)+"\n\n"+error_action(str(exc))))
            except Exception as exc:
                if outcome([str(exc)], self.stop_requested) == "stopped":
                    self.events.put(("stopped", "Copie interrompue. Cliquez sur Reprendre avec les mêmes dossiers ; les données seront vérifiées."))
                else:
                    self.events.put(("error", str(exc)+"\n\n"+error_action(str(exc))))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, n, total, elapsed = event
                    self.bar.stop()
                    self.bar.configure(mode="determinate")
                    self.bar["value"] = n/max(total, 1)*100
                    if not self.stop_requested:
                        self.status.set(f"Copie : {n/1e9:.3f}/{total/1e9:.3f} Go · {n/max(elapsed, .001)/1e6:.1f} Mo/s\nLa vérification finale suit la copie.")
                elif event[0] == "phase":
                    if not self.stop_requested:
                        self.status.set(event[1])
                    if event[1].startswith("Vérification finale"):
                        self.bar.configure(mode="indeterminate")
                        self.bar.start(12)
                elif event[0] == "open_error":
                    messagebox.showerror("Dossier indisponible", "Impossible d'ouvrir le gestionnaire de fichiers.\nOuvrez manuellement ce dossier, s'il existe encore :\n"+event[1])
                elif event[0] == "report_data":
                    self.report_data = event[1]
                else:
                    self.bar.stop()
                    self.bar.configure(mode="determinate")
                    self.set_running(False)
                    self.begin.configure(text="Copier / reprendre" if event[0] == "done" else "Reprendre")
                    self.report.configure(state="normal")
                    self.status.set(event[1])
                    self.report_kind = event[0]
                    self.report_message = event[1]
                    if event[0] == "done":
                        self.verified_destination = self.last_destination
                        self.result_button.configure(state="normal")
                        self.bar["value"] = 100
                    elif event[0] == "error":
                        messagebox.showerror("Transfert incomplet", event[1])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def open_destination(self):
        if self.running or not self.verified_destination:
            return
        threading.Thread(target=self._open_destination, args=(self.verified_destination,), daemon=True).start()

    def _open_destination(self, directory):
        # L'accès à un lecteur réseau peut attendre le système ; ne pas bloquer Tk.
        path = Path(directory)
        try:
            path = path.resolve()
            if not path.is_dir():
                raise OSError("Dossier déplacé ou supprimé")
            if sys.platform == "win32":
                os.startfile(str(path))
            else:
                command = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.run([command, str(path)], check=True, timeout=5,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, RuntimeError, subprocess.SubprocessError):
            self.events.put(("open_error",str(path)))

    def show_report(self):
        if self.running or not getattr(self, "report_kind", None):
            return
        title, content = render_report(self.report_data, self.report_kind, self.last_destination, self.report_message)
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("760x590")
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", width=80, height=26)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.insert("1.0", content)
        text.configure(state="disabled")

    def close(self):
        setup = getattr(self, "setup_window", None)
        if setup is not None and setup.running:
            if getattr(setup, "_starting", False):
                setup.stop_share()
                self.status.set("Annulation de la préparation du partage demandée. Attendez le résultat, puis fermez.")
                return
            messagebox.showinfo("Préparation en cours", "Attendez la fin de la préparation de l'invitation avant de fermer.")
            return
        if setup is not None and setup.session.active:
            setup.stop_share()
            self.status.set("Arrêt du partage demandé. Attendez le résultat, puis fermez.")
            return
        if self.running:
            self.request_stop()
        else:
            self.root.destroy()


def launch():
    root = tk.Tk()
    App(root)
    root.mainloop()
