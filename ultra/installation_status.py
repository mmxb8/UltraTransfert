"""Avis source informatif ; ne constitue jamais une autorisation de transfert."""
import json
from pathlib import Path


def installation_notice(project=None):
    root=Path(project) if project is not None else Path(__file__).resolve().parent.parent
    try:
        path=root/'reports/installation.json'
        with path.open('rb') as stream:data=stream.read(32769)
        if len(data)>32768:return None
        report=json.loads(data)
        if (isinstance(report,dict) and report.get('core_ready') is True
                and report.get('sharing_ready') is False):
            return ('Copies et réception disponibles. Pour créer une nouvelle connexion HTTPS, '
                    'relancez Installer_Windows.bat avec Internet. Une connexion conservée reste rechargeable.')
    except (OSError,ValueError,TypeError):
        pass
    return None
