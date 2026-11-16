"""Échec du premier lancement visible, même pour un EXE sans console."""
import ctypes
import os
from pathlib import Path
import sys
import tempfile
import traceback


def diagnostic(exc, directory=None):
    """Journal neuf, sans écrasement ni variables locales ; erreur disque tolérée."""
    path = None
    try:
        if directory is None:
            if sys.platform == 'win32' and os.environ.get('LOCALAPPDATA'):
                base = Path(os.environ['LOCALAPPDATA'])
            else:
                base = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')
            directory = base/'UltraTransfert'/'diagnostics'
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(prefix='demarrage-', suffix='.log', dir=directory)
        path = Path(name)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            from . import __version__
            output.write(f'UltraTransfert {__version__} | {sys.platform} | Python {sys.version.split()[0]}\n')
            # Ne pas capturer les variables locales ni les fichiers transférés.
            text = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            output.write(text[-65536:])
        return path
    except Exception:
        if path is not None:
            try:
                path.unlink()
            except OSError:
                pass
        return None


def native_message(text):
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    show = user32.MessageBoxW
    show.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    show.restype = ctypes.c_int
    if not show(None, text, 'UltraTransfert : lancement impossible', 0x10):
        raise OSError('Message Windows indisponible')


def report_failure(exc):
    path = diagnostic(exc)
    text = ('UltraTransfert ne peut pas ouvrir son interface.\n\n'
            'Vérifiez que tout le ZIP a été extrait dans un dossier personnel. '
            'Pour le portable, conservez le dossier _internal avec UltraTransfert.exe. '
            'Pour les sources, relancez Installer_Windows.bat.\n\n'
            'Conservez les sources et les données partielles pour une reprise.\n\n')
    text += ('Diagnostic : '+str(path)+'\nConservez ce fichier pour demander de l’aide.' if path else
             'Le diagnostic n’a pas pu être enregistré. Vérifiez l’espace libre et les droits du dossier personnel.')
    try:
        if sys.platform == 'win32':
            native_message(text)  # Ne dépend pas de tkinter/Tcl, potentiellement cassé.
            return
    except Exception:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        try:
            root.withdraw()
            messagebox.showerror('UltraTransfert : lancement impossible', text, parent=root)
        finally:
            root.destroy()
    except Exception:
        try:
            print(text, file=sys.stderr)
        except Exception:
            pass


def launch_safely(launch=None):
    try:
        if launch is None:
            from .gui import launch
        launch()
        return 0
    except Exception as exc:
        report_failure(exc)
        return 1
