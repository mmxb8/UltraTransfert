"""Contrôle développeur : reprise et, en paquet autonome, TLS local temporaire."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import tempfile
import threading
import time

from . import __version__
from .engine import LocalSource, Options, Transfer, digest


def check(require_gui=True):
    started = time.perf_counter()
    if require_gui:
        import tkinter as tk
        from .gui import App
        root = tk.Tk()
        try:
            root.withdraw()
            App(root)
            root.update()
        finally:
            root.destroy()
    sharing_prepared = False
    sharing_session_checked = False
    sharing_restore_checked = False
    with tempfile.TemporaryDirectory(prefix="UltraTransfert contrôle ") as temp:
        if getattr(sys, "frozen", False) or getattr(sys, '_ultra_installed', False):
            from .share_setup import prepare_share
            prepared = prepare_share("https://localhost:8443", Path(temp)/"connexion privée")
            sharing_prepared = True
            from .share_restore import load_prepared_share
            restored = load_prepared_share(prepared.directory)
            if restored.certificate_sha256 != prepared.certificate_sha256:
                raise RuntimeError("Connexion embarquée restaurée incohérente.")
            sharing_restore_checked = True
        src, dst = Path(temp)/"source été", Path(temp)/"destination"
        src.mkdir()
        data = bytes(range(256))*8192
        name = "données_日本語.bin"
        (src/name).write_bytes(data)
        (src/".caché").write_bytes(b"hidden")
        (src/"vide").touch()
        (src/"dossier vide").mkdir()
        cancel = threading.Event()
        def progress(n, total):
            if n >= 65536:
                cancel.set()
        first = Transfer(LocalSource(src), dst, Options(workers=1, buffer_size=65536),
                         progress, cancel).run()
        if not first.errors:
            raise RuntimeError("Le contrôle d'interruption n'a pas interrompu la copie.")
        result = Transfer(LocalSource(src), dst, Options(workers=1, buffer_size=65536)).run()
        expected = hashlib.sha256(data).hexdigest()
        if result.errors or result.resumed_bytes <= 0 or digest(dst/name) != expected:
            raise RuntimeError(f"Échec du contrôle de reprise : {result.errors}")
        if not (dst/"dossier vide").is_dir() or (dst/"vide").stat().st_size != 0:
            raise RuntimeError("Éléments vides perdus.")
        if (src/name).read_bytes() != data or (dst/".caché").read_bytes() != b"hidden":
            raise RuntimeError("Contenu source ou destination incorrect.")
        if sharing_prepared:
            import socket
            from .invitation import write_invitation, read_invitation
            from .share_setup import PreparedShare
            from .share_session import ShareSession
            with socket.socket() as reserve:
                reserve.bind(("127.0.0.1", 0))
                port = reserve.getsockname()[1]
            url = f"https://localhost:{port}"
            invite = Path(temp)/"smoke.utconnect"
            write_invitation(url, prepared.directory/"server-cert.pem", prepared.directory/"token.txt", invite)
            selected = PreparedShare(prepared.directory, invite, url, prepared.certificate_sha256)
            session = ShareSession()
            try:
                session.start(src, selected)
                remote_result = Transfer(read_invitation(invite).remote_source(), Path(temp)/"destination TLS").run()
                if remote_result.errors or digest(Path(temp)/"destination TLS"/name) != expected:
                    raise RuntimeError("Le partage TLS embarqué n'est pas vérifié.")
            finally:
                session.stop()
            if session.active:
                raise RuntimeError("Le partage embarqué n'est pas arrêté.")
            sharing_session_checked = True
    environment = sys.platform
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.WinDLL('ntdll').wine_get_version
            environment = 'wine'
        except AttributeError:
            environment = 'windows'
    return {"status": "passed", "version": __version__, "platform": sys.platform,
            'execution_environment': environment,
            'installed': bool(getattr(sys, '_ultra_installed', False)),
            "machine": platform.machine(), "frozen": bool(getattr(sys, "frozen", False)),
            "gui_created": require_gui, "sharing_prepared": sharing_prepared, "sharing_session_checked": sharing_session_checked, "sharing_restore_checked": sharing_restore_checked, "sha256": expected,
            "resumed_bytes": result.resumed_bytes, "files": result.files,
            "seconds": time.perf_counter()-started}


def write_report(path, require_gui=True):
    try:
        result = check(require_gui)
    except Exception as exc:
        result = {"status": "failed", "version": __version__, "error": str(exc)}
    Path(path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["status"] == "passed" else 1
