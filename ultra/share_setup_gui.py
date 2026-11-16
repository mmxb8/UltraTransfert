"""Préparation hors ligne, puis partage explicite avec arrêt des connexions."""
from datetime import datetime
from pathlib import Path
import queue
import secrets
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .share_setup import prepare_share
from .share_restore import load_prepared_share
from .share_session import ShareSession
from .invitation import origin
from .engine import OperationCancelled


class SetupDialog:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Émettre des fichiers en HTTPS")
        self.window.geometry("780x650")
        self.running = False
        self._starting = False
        self.events = queue.Queue()
        self.prepared = None
        self.session = ShareSession()
        self._close_after_stop = False
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Émettre des fichiers", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="1. Préparer la connexion   2. Choisir le dossier   3. Partager explicitement", wraplength=700).pack(anchor="w", pady=8)
        ttk.Label(frame, text="Adresse HTTPS du poste émetteur (IPv4 précise ou localhost, avec le port)").pack(anchor="w")
        self.url = tk.StringVar(value="https://localhost:8443")
        self.address = ttk.Entry(frame, textvariable=self.url)
        self.address.pack(fill="x", pady=6)
        ttk.Label(frame, text="localhost fonctionne sur ce poste uniquement. Pour deux postes, indiquez l'IPv4 réelle de l'émetteur. Le réseau et le pare-feu restent à configurer.", wraplength=700).pack(anchor="w")
        self.prepare_button = ttk.Button(frame, text="Créer les fichiers de connexion…", command=self.prepare)
        self.prepare_button.pack(anchor="w", pady=(12, 4))
        self.load_button = ttk.Button(frame, text="Charger une connexion existante…", command=self.load_existing)
        self.load_button.pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, text="Dossier à partager en lecture seule").pack(anchor="w")
        source_row = ttk.Frame(frame)
        source_row.pack(fill="x", pady=6)
        self.source = tk.StringVar()
        self.source_entry = ttk.Entry(source_row, textvariable=self.source)
        self.source_entry.pack(side="left", fill="x", expand=True)
        self.source_button = ttk.Button(source_row, text="Parcourir…", command=self.choose_source)
        self.source_button.pack(side="left", padx=8)
        ttk.Label(frame, text="Toute personne possédant l'invitation peut lire ce dossier pendant le partage. Aucune ouverture de pare-feu n'est effectuée.", wraplength=720).pack(anchor="w", pady=4)
        self.predictive = tk.BooleanVar(value=False)
        self.predictive_box = ttk.Checkbutton(frame, text="Compression prédictive R2.2 / lecture R3.1 (essai, activer aussi à la réception)", variable=self.predictive)
        self.predictive_box.pack(anchor="w")
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=8)
        self.start_button = ttk.Button(actions, text="Partager ce dossier", command=self.start_share, state="disabled")
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Arrêter le partage", command=self.stop_share, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        output = ttk.Frame(frame)
        output.pack(fill="both", expand=True)
        self.result = tk.Text(output, wrap="word", height=12)
        scrollbar = ttk.Scrollbar(output, orient="vertical", command=self.result.yview)
        self.result.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.result.pack(side="left", fill="both", expand=True)
        self.show("Choisissez un dossier personnel de configuration, hors du dossier de données à partager. Seul acces.utconnect sera à transmettre au destinataire de confiance.")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = self.window.after(100, self.poll)

    def show(self, text):
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text)
        self.result.configure(state="disabled")

    def prepare(self):
        if self.running or self.session.active:
            return
        parent = filedialog.askdirectory(parent=self.window, title="Dossier personnel de configuration, hors des données à partager")
        if not parent:
            return
        destination = Path(parent)/("UltraTransfert-connexion-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+secrets.token_hex(4))
        url = self.url.get()
        self.prepared = None
        self.running = True
        self.set_controls()
        self.show("Préparation locale en cours… Aucun service n'est démarré.")
        def work():
            try:
                self.events.put(("done", prepare_share(url, destination)))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def load_existing(self):
        if self.running or self.session.active:
            return
        directory = filedialog.askdirectory(parent=self.window, title="Dossier privé contenant certificat, clé, jeton et acces.utconnect")
        if not directory:
            return
        self.prepared = None
        self.running = True
        self.set_controls()
        self.show("Validation locale de la connexion sauvegardée… Aucun partage n'est ouvert.")
        def work():
            try:
                self.events.put(("loaded", load_prepared_share(directory)))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def choose_source(self):
        if self.running or self.session.active:
            return
        path = filedialog.askdirectory(parent=self.window, title="Dossier à partager en lecture seule")
        if path:
            self.source.set(path)

    def set_controls(self):
        busy = self.running or self.session.active
        for widget in (self.address, self.prepare_button, self.load_button, self.source_entry, self.source_button):
            widget.configure(state="disabled" if busy else "normal")
        if getattr(self, "predictive_box", None) is not None:
            self.predictive_box.configure(state="disabled" if busy else "normal")
        self.start_button.configure(state="normal" if not busy and self.prepared is not None else "disabled")
        starting = getattr(self, "_starting", False)
        self.stop_button.configure(text="Annuler la préparation" if starting else "Arrêter le partage",
                                   state="normal" if starting or (self.session.active and not self.running) else "disabled")

    def start_share(self):
        if self.running or self.session.active:
            return
        try:
            if self.prepared is None:
                raise ValueError("Préparez d'abord la connexion.")
            if origin(self.url.get()) != self.prepared.url:
                raise ValueError("L'adresse a changé : préparez une nouvelle invitation avant de partager.")
            source = self.source.get()
            if not source:
                raise ValueError("Choisissez le dossier à partager.")
        except Exception as exc:
            messagebox.showerror("Partage impossible", str(exc), parent=self.window)
            return
        compression = "predictive" if getattr(self, "predictive", None) is not None and self.predictive.get() else "auto"
        self.running = True
        self._starting = True
        self._start_cancel = threading.Event()
        self._close_after_stop = False
        self.set_controls()
        self.show("Inventaire et vérification de la source… Le partage ne sera annoncé prêt qu'après préparation complète.")
        def work():
            try:
                source_label = str(Path(source).resolve())
                url = (self.session.start(source, self.prepared, cancel=self._start_cancel, compression=compression)
                       if compression == "predictive" else self.session.start(source, self.prepared, cancel=self._start_cancel))
                if self._start_cancel.is_set():
                    self.session.stop()
                    self.events.put(("cancelled", None))
                else:
                    self.events.put(("sharing", (source_label, url)))
            except OperationCancelled:
                self.events.put(("cancelled", None))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def stop_share(self, close_after=False):
        if self.running and getattr(self, "_starting", False):
            self._close_after_stop = self._close_after_stop or close_after
            self._start_cancel.set()
            self.stop_button.configure(state="disabled")
            self.show("Annulation demandée… Attendez la fin de l'opération disque en cours. Aucun partage ne sera annoncé prêt.")
            return
        if self.running or not self.session.active:
            return
        self._close_after_stop = close_after
        self.running = True
        self.set_controls()
        self.show("Arrêt du partage et fermeture des connexions en cours…")
        def work():
            try:
                self.session.stop()
                self.events.put(("stopped", None))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            kind, value = self.events.get_nowait()
            self.running = False
            self._starting = False
            if kind == "sharing" and self._start_cancel.is_set():
                self.stop_share(close_after=self._close_after_stop)
                self._poll_id = self.window.after(100, self.poll)
                return
            if kind in ("done", "loaded"):
                self.prepared = value
                self.url.set(value.url)
                self.show(f"Connexion prête :\n{value.invitation_path}\n\nAdresse : {value.url}\nEmpreinte du certificat :\n{value.certificate_sha256}\n\nTransmettez seulement l'invitation par un canal de confiance et comparez cette empreinte. Gardez la clé privée et token.txt sur ce poste.\n\nAucun partage n'est ouvert. Choisissez le dossier puis cliquez sur Partager ce dossier.")
            elif kind == "sharing":
                source, url = value
                self.show(f"PARTAGE OUVERT EN LECTURE SEULE\nDossier : {source}\nAdresse : {url}\n\nInvitation : {self.prepared.invitation_path}\nEmpreinte : {self.prepared.certificate_sha256}\n\nUn accès secret valide est nécessaire pour demander les données. Gardez cette fenêtre ouverte ; utilisez Arrêter le partage à la fin.")
            elif kind == "cancelled":
                self.show("Préparation annulée. Aucun partage actif. Choisissez le dossier puis Partager pour recommencer.")
            elif kind == "stopped":
                self.show("Partage arrêté. L'écoute et les connexions suivies sont fermées. Les données déjà reçues restent sur le destinataire. Redémarrer avec cette même préparation réactive la même invitation.")
            else:
                self._close_after_stop = False
                self.show("Opération impossible : "+value)
                messagebox.showerror("Opération impossible", value, parent=self.window)
            self.set_controls()
            if kind in ("stopped", "cancelled") and self._close_after_stop:
                self.close()
                return
        except queue.Empty:
            pass
        self._poll_id = self.window.after(100, self.poll)

    def close(self):
        if self.running:
            if getattr(self, "_starting", False):
                self.stop_share(close_after=True)
                return
            messagebox.showinfo("Opération en cours", "Attendez le résultat avant de fermer.", parent=self.window)
            return
        if self.session.active:
            self.stop_share(close_after=True)
            return
        self.window.after_cancel(self._poll_id)
        self.window.destroy()
