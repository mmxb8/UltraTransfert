"""Explicit developer checks. Never executed by normal application startup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import sys
import tempfile
import threading
import time

from .engine import LocalSource, Options, Transfer, digest


def native_windows():
    if sys.platform != 'win32':
        return False
    import ctypes
    try:
        ctypes.WinDLL('ntdll').wine_get_version
        return False
    except AttributeError:
        return True


def fixture(root):
    (root/'vide').mkdir()
    (root/'zéro').touch()
    (root/'données_日本語.bin').write_bytes(random.Random(20261116).randbytes(4*1024*1024+271))
    (root/'signal.bin').write_bytes(b''.join(struct.pack('<I', i) for i in range(262144)))
    for i in range(32):
        (root/f'petit-{i:02}.txt').write_text('UltraTransfert contrôle intégrité\n'*i, encoding='utf-8')
    return {p.relative_to(root).as_posix(): digest(p) for p in root.rglob('*') if p.is_file()}


def copy_resume(origin, destination, expected):
    cancel = threading.Event()
    def progress(n, total):
        if n >= 65536:
            cancel.set()
    options = Options(workers=1, buffer_size=65536)
    first = Transfer(origin, destination, options, progress=progress, cancel=cancel).run()
    if not first.errors or not cancel.is_set():
        raise RuntimeError('Le scénario ne prouve pas une interruption.')
    result = Transfer(origin, destination, options).run()
    if result.errors or result.resumed_bytes <= 0:
        raise RuntimeError('Reprise échouée : '+str(result.errors))
    for name, sha in expected.items():
        if digest(destination/name) != sha:
            raise RuntimeError('Empreinte différente : '+name)
    if not (destination/'vide').is_dir():
        raise RuntimeError('Dossier vide perdu.')
    return {'files_checked':len(expected), 'resumed_bytes':result.resumed_bytes,
            'sha256_verified':True, 'interruption_and_resume':True}


def predictive_check():
    from .share_setup import prepare_share
    from .network import make_server, RemoteSource
    from .compression import codecs
    with tempfile.TemporaryDirectory(prefix='UltraTransfert validation ') as temp:
        base = Path(temp)
        src = base/'source'; src.mkdir()
        expected = fixture(src)
        prepared = prepare_share('https://localhost:8443', base/'private')
        token = (prepared.directory/'token.txt').read_text().strip()
        server = make_server(LocalSource(src), ('127.0.0.1',0), prepared.directory/'server-cert.pem',
                             prepared.directory/'server-key.pem', token, 'predictive', link_mbps=50)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        remote = None
        try:
            remote = RemoteSource(f'https://localhost:{server.server_port}', token,
                                  prepared.directory/'server-cert.pem', 'predictive')
            result = copy_resume(remote, base/'received', expected)
            entry = next(e for e in remote.entries if e.path=='données_日本語.bin')
            with remote.open_range(entry, 17, 65539) as stream:
                got = stream.read(65540)
            if got != (src/entry.path).read_bytes()[17:17+65539]:
                raise RuntimeError('Plage partielle incorrecte.')
            from .engine import TransferError
            legacy = RemoteSource(f'https://localhost:{server.server_port}', token,
                                  prepared.directory/'server-cert.pem', 'ultra')
            try:
                try:
                    with legacy.open(entry):
                        pass
                except TransferError:
                    pass
                else:
                    raise RuntimeError('Un ancien client ne doit pas recevoir un format prédictif non négocié.')
            finally:
                legacy.release_connections()
            result.update(legacy_client_refused=True, range_checked=True, tls_certificate_verified=True,
                          available_codecs=codecs(), wire_format='x-ultra-predictive-v1')
            return result
        finally:
            if remote is not None:
                remote.release_connections()
            server.shutdown(); server.server_close(); thread.join(timeout=5)


def rdp_check(source_parent, destination_parent):
    # Refuse Linux, Wine and local-only simulations before making any directory.
    if not native_windows():
        raise RuntimeError('Un véritable Windows est requis ; Wine ne constitue pas une validation RDP.')
    import ctypes
    if not ctypes.windll.user32.GetSystemMetrics(0x1000):
        raise RuntimeError('Exécuter ce contrôle dans une session Bureau à distance active.')
    parents = [Path(source_parent), Path(destination_parent)]
    if not any(str(p).lower().startswith('\\\\tsclient\\') for p in parents):
        raise RuntimeError('Sélectionner au moins un dossier sur un lecteur RDP \\\\tsclient\\ autorisé.')
    if any(not p.is_dir() for p in parents):
        raise RuntimeError('Les deux dossiers parents doivent déjà exister.')
    # Each TemporaryDirectory creates a fresh private child; user files are never overwritten.
    with tempfile.TemporaryDirectory(prefix='UltraTransfert-RDP-source-', dir=parents[0]) as a, \
         tempfile.TemporaryDirectory(prefix='UltraTransfert-RDP-destination-', dir=parents[1]) as b:
        src, dst = Path(a), Path(b)
        expected = fixture(src)
        result = copy_resume(LocalSource(src), dst, expected)
    result.update(remote_session_detected=True, redirected_drive_tested=True,
                  native_virtual_channel_tested=False, session_disconnect_reconnect_tested=False)
    return result


def write_report(kind, report_path, source=None, destination=None):
    started = time.perf_counter()
    report = {'status':'failed', 'check':kind, 'native_windows':native_windows()}
    try:
        report['details'] = predictive_check() if kind=='predictive' else rdp_check(source, destination)
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = str(exc)
    report['seconds'] = time.perf_counter()-started
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return 0 if report['status']=='passed' else 1


def rdp_wizard():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root = tk.Tk(); root.withdraw()
    try:
        messagebox.showinfo('Contrôle RDP', 'Dans une session RDP active, choisissez un dossier source et un dossier destination. Au moins un doit être sur \\\\tsclient\\. Seuls des fichiers de test temporaires seront créés puis retirés.', parent=root)
        source = filedialog.askdirectory(title='Dossier parent source du test RDP', parent=root)
        if not source: return 2
        destination = filedialog.askdirectory(title='Dossier parent destination du test RDP', parent=root)
        if not destination: return 2
        report = filedialog.asksaveasfilename(title='Enregistrer le rapport RDP', initialfile='UltraTransfert-RDP.json', defaultextension='.json', parent=root)
        if not report: return 2
        code = write_report('rdp', report, source, destination)
        data = json.loads(Path(report).read_text(encoding='utf-8'))
        (messagebox.showinfo if code==0 else messagebox.showerror)('Contrôle RDP', 'Test réussi. Rapport : '+report if code==0 else data['error'], parent=root)
        return code
    finally:
        root.destroy()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('kind', choices=['predictive','rdp','rdp-wizard'])
    p.add_argument('--report')
    p.add_argument('--source'); p.add_argument('--destination')
    a=p.parse_args()
    if a.kind=='rdp-wizard': raise SystemExit(rdp_wizard())
    if not a.report or (a.kind=='rdp' and (not a.source or not a.destination)):
        p.error('--report requis ; RDP exige aussi --source et --destination')
    raise SystemExit(write_report(a.kind,a.report,a.source,a.destination))
