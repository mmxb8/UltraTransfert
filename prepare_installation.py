"""Préparer les sources sans rendre pip/Internet obligatoires pour le moteur."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import venv

ROOT = Path(__file__).resolve().parent
PROBE = '''import json,sys,tkinter
from pathlib import Path
from ultra.smoke import check
assert sys.version_info >= (3,10)
assert Path(sys.prefix).resolve()==Path(sys.argv[1]).resolve(), 'Interpréteur hors environnement isolé'
tkinter.Tcl().eval('info patchlevel')
result=check(require_gui=False)
assert result['status']=='passed'
print(json.dumps(result))'''
SHARING_PROBE = "import cryptography; assert cryptography.__version__ == '50.0.2'; from cryptography import x509; from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID; from cryptography.hazmat.primitives import hashes,serialization; from cryptography.hazmat.primitives.asymmetric import rsa"


class InstallationLocked(FileExistsError):
    pass


def prepare(project=ROOT, offline=False, progress=None):
    notify=progress or (lambda text:None)
    project=Path(project).resolve()
    lock=project/'.cycle.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise InstallationLocked('Préparation déjà verrouillée') from None
    try:
        try:os.write(fd,str(os.getpid()).encode())
        finally:os.close(fd)
    except BaseException:
        lock.unlink()
        raise
    started=time.perf_counter()
    report={'core_ready':False,'sharing_ready':False,'offline':offline,'platform':sys.platform,'gui_visually_checked':False,'sharing_reused':False,'sharing_install_attempted':False}
    try:
        reports=project/'reports';reports.mkdir(exist_ok=True)
        notify('1/3 Préparation de l’environnement isolé…')
        environment=project/'.venv-run'
        python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if environment.is_symlink():raise RuntimeError('Environnement lié refusé ; choisissez un dossier réel.')
        if environment.exists():
            if not (environment/'pyvenv.cfg').is_file() or not python.is_file():
                raise RuntimeError('Le dossier .venv-run existant est incomplet. Conservez-le et préparez une nouvelle extraction du ZIP.')
        else:
            # Le moteur et tkinter n'ont besoin d'aucun paquet PyPI.
            venv.EnvBuilder(with_pip=False,symlinks=os.name!='nt').create(environment)
        env=os.environ.copy()
        for key in ('PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        def run(args,timeout=120):
            return subprocess.run([str(python),*args],cwd=project,env=env,capture_output=True,text=True,errors='replace',timeout=timeout)
        notify('2/3 Contrôle du moteur, de Tcl et de la copie/reprise…')
        probe=run(['-c',PROBE,str(environment)],30)
        if probe.returncode:
            (reports/'installation-core.log').write_text(probe.stdout+probe.stderr,encoding='utf-8')
            raise RuntimeError('Contrôle du moteur/Tcl impossible. Voir reports/installation-core.log ; aucun lancement annoncé prêt.')
        report['core_probe']=json.loads(probe.stdout)
        report['core_ready']=True
        # Diagnostic de dépendance ; aucune écoute ou génération de secret.
        report['sharing_ready']=run(['-c',SHARING_PROBE],20).returncode==0
        report['sharing_reused']=report['sharing_ready']
        if report['sharing_ready']:
            notify('3/3 Complément déjà prêt ; aucune installation ni requête réseau.')
        else:
            notify('3/3 Complément de connexion : vérification locale uniquement.' if offline else '3/3 Préparation du complément facultatif ; le moteur reste utilisable en cas d’échec réseau…')
        if not offline and not report['sharing_ready']:
            report['sharing_install_attempted']=True
            try:
                pip=run(['-m','pip','--version'],20)
                if pip.returncode:
                    boot=run(['-m','ensurepip'],60)
                    (reports/'installation-pip.log').write_text(boot.stdout+boot.stderr,encoding='utf-8')
                    if boot.returncode:raise RuntimeError('Initialisation pip indisponible')
                result=run(['-m','pip','install','--only-binary=:all:','--timeout','10','--retries','0','-r',str(project/'requirements-sharing.txt')],120)
                (reports/'installation-sharing.log').write_text(result.stdout+result.stderr,encoding='utf-8')
                report['sharing_install_succeeded']=result.returncode==0
                report['sharing_ready']=run(['-c',SHARING_PROBE],20).returncode==0
            except (OSError,RuntimeError,subprocess.SubprocessError):
                report['sharing_install_succeeded']=False
                report['sharing_ready']=run(['-c',SHARING_PROBE],20).returncode==0
        report['status']='ready' if report['sharing_ready'] else 'core_ready_without_new_connections'
    except Exception as exc:
        report['error']=str(exc)
        report['status']='core_ready_without_new_connections' if report['core_ready'] else 'failed'
    finally:
        report['seconds']=time.perf_counter()-started
        try:
            target=project/'reports'/'installation.json'
            target.parent.mkdir(exist_ok=True)
            pending=target.with_suffix('.pending')
            # Rapport local de préparation, sans clé, certificat ou jeton.
            created=False
            try:
                fd=os.open(pending,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);created=True
                with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
                os.replace(pending,target);created=False
            finally:
                if created:pending.unlink(missing_ok=True)
        finally:lock.unlink()
    return report


def main():
    parser=argparse.ArgumentParser(description='Préparer UltraTransfert sans dépendance réseau obligatoire pour les copies.')
    parser.add_argument('--offline',action='store_true',help='Ne pas installer pip ou le complément ; aucune requête réseau')
    args=parser.parse_args()
    try:report=prepare(offline=args.offline,progress=lambda text:print(text,flush=True))
    except InstallationLocked:
        print('Une préparation ou construction détient le verrou. Attendez sa fin ; aucun verrou supprimé.')
        return 1
    except (OSError,ValueError) as exc:
        print('Préparation impossible : '+str(exc));return 1
    if not report['core_ready']:
        print('Préparation non terminée : '+report.get('error','voir reports/installation.json'));return 1
    print('Copies et réception HTTPS prêtes. Aucun service ouvert.')
    if not report['sharing_ready']:
        print('Création de nouvelles connexions HTTPS non disponible : relancez Installer_Windows.bat avec Internet pour ajouter le complément. Les connexions conservées restent rechargeables.')
    return 0


if __name__=='__main__':raise SystemExit(main())
