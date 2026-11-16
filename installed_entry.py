"""Point d'entrée du runtime privé ; aucun Python du poste n'est utilisé."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys._ultra_installed = True
os.environ['TCL_LIBRARY'] = str(ROOT/'runtime/tcl/tcl9.0')
os.environ['TK_LIBRARY'] = str(ROOT/'runtime/tcl/tk9.0')


def install_check(report_path):
    """Contrôle hors ligne, sans port d'écoute ni paiement."""
    try:
        from ultra.install_integrity import verify_payload
        verify_payload(ROOT)
        import tkinter as tk
        from ultra.donations import QR_PATH
        from ultra import __version__
        import cryptography
        import zstandard
        root = tk.Tk()
        root.withdraw()
        try:
            image = tk.PhotoImage(master=root, file=str(QR_PATH))
            if image.width() < 200:
                raise RuntimeError('QR code incomplet.')
            root.update()
        finally:
            root.destroy()
        from ultra.smoke import check
        # Le contrôle de copie source ne crée pas de service ; le test TLS complet
        # est réservé à --smoke-test, explicitement demandé par le développeur.
        sys._ultra_installed = False
        try:
            copy = check(require_gui=False)
        finally:
            sys._ultra_installed = True
        report = {'status':'passed', 'version':__version__, 'copy':copy,
                  'cryptography':cryptography.__version__, 'zstandard':zstandard.__version__,
                  'gui_resources_loaded':True, 'network_listener_started':False}
    except Exception as exc:
        report = {'status':'failed', 'error':str(exc)}
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['status'] == 'passed' else 1


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--install-check':
        return install_check(sys.argv[2])
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        from ultra.smoke import write_report
        return write_report(sys.argv[2])
    if len(sys.argv) == 3 and sys.argv[1] == '--predictive-test':
        from ultra.validation import write_report
        return write_report('predictive', sys.argv[2])
    from ultra.startup import launch_safely
    return launch_safely()


if __name__ == '__main__':
    raise SystemExit(main())
