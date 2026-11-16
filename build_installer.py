"""Véritable installateur NSIS, construit depuis des dépendances verrouillées.

Construction de référence : Linux x64, Python 3.12+, nsis et msitools.
Ce compilateur croisé ne constitue PAS une validation Windows.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

from ultra import __version__

ROOT = Path(__file__).resolve().parent


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def extract_zip(path, destination):
    """Refuser liens, traversées et chemins Windows avant toute extraction."""
    with zipfile.ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 300*1024*1024:
            raise ValueError('Archive de dépendance trop grande.')
        for item in archive.infolist():
            name = item.filename.rstrip('/')
            p = PurePosixPath(name)
            if (not name or p.is_absolute() or '..' in p.parts or '\\' in name
                    or ':' in name or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('Entrée ZIP interdite : '+item.filename)
        archive.extractall(destination)


def fetch_inputs(cache, offline=False):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT/'installer/inputs.lock.json').read_text())
    for entry in lock['inputs']:
        name = entry['name']
        if Path(name).name != name:
            raise ValueError('Nom de dépendance invalide.')
        path = cache/name
        if not path.exists():
            if offline:
                raise FileNotFoundError('Dépendance hors ligne absente : '+name)
            if not entry['url'].startswith(('https://www.python.org/', 'https://files.pythonhosted.org/')):
                raise ValueError('Source de dépendance non autorisée.')
            request = urllib.request.Request(entry['url'], headers={'User-Agent':'UltraTransfert-build/0.4'})
            with urllib.request.urlopen(request, timeout=90) as response:
                data = response.read(100*1024*1024+1)
            if len(data) > 100*1024*1024 or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Téléchargement non conforme : '+name)
            path.write_bytes(data)
        if sha256(path) != entry['sha256']:
            raise ValueError('Empreinte de dépendance incorrecte : '+name)
    return lock


def stage_payload(cache, stage, msiextract):
    cache, stage = Path(cache), Path(stage)
    if stage.exists():
        raise FileExistsError('Le dossier de préparation doit être neuf.')
    runtime = stage/'runtime'
    runtime.mkdir(parents=True)
    extract_zip(cache/'python-3.14.10-embed-amd64.zip', runtime)
    with tempfile.TemporaryDirectory(prefix='UltraTransfert-tcl-') as temp:
        tcl = Path(temp)
        subprocess.run([msiextract, '-C', str(tcl), str(cache/'tcltk.msi')], check=True, stdout=subprocess.DEVNULL)
        for path in (tcl/'DLLs').iterdir():
            if path.suffix in ('.pyd', '.dll'):
                shutil.copy2(path, runtime/path.name)
        shutil.copytree(tcl/'Lib/tkinter', runtime/'Lib/tkinter', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'test'))
        for name, target in [('libtcl9.0.4.zip', 'tcl9.0'), ('libtk9.0.4.zip', 'tk9.0')]:
            extracted = tcl/target
            extract_zip(tcl/'tcl'/name, extracted)
            source = next(extracted.iterdir())
            shutil.copytree(source, runtime/'tcl'/target)
        for name in ('dde1.4', 'registry1.3'):
            shutil.copytree(tcl/'tcl'/name, runtime/'tcl'/name)
    site = runtime/'Lib/site-packages'
    site.mkdir(parents=True)
    for path in cache.glob('*.whl'):
        # Ne déployer que les roues présentes dans le verrou, pas d'autres fichiers du cache.
        names = {e['name'] for e in json.loads((ROOT/'installer/inputs.lock.json').read_text())['inputs']}
        if path.name in names:
            extract_zip(path, site)
    (runtime/'python314._pth').write_text('python314.zip\n.\nLib\nLib/site-packages\n..\n', encoding='utf-8')
    shutil.copytree(ROOT/'ultra', stage/'ultra', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('installed_entry.py', 'LICENSE', 'DONS_BITCOIN.md', 'SECURITY.md', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT/name, stage/name)
    shutil.copy2(ROOT/'installer/ultra.ico', stage/'ultra.ico')
    shutil.copy2(ROOT/'installer/Tester_RDP.bat', stage/'Tester_RDP.bat')
    (stage/'LIRE_MOI.txt').write_text((ROOT/'installer/UTILISATEUR.txt').read_text(encoding='utf-8'), encoding='utf-8')
    # Les sources complètes sont offertes hors ligne, avec les scripts de construction.
    with zipfile.ZipFile(stage/'SOURCES.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            relative = p.relative_to(ROOT)
            if (p.is_file() and not p.is_symlink() and not any(s in {'dist','bin','build','__pycache__','.venv-run','.git','.installer-cache'} or s.endswith('.egg-info') for s in relative.parts)
                    and not p.name.endswith(('.pyc','.pending','.lock'))):
                z.write(p, relative)
    entries = {p.relative_to(stage).as_posix():sha256(p) for p in sorted(stage.rglob('*')) if p.is_file()}
    (stage/'payload-manifest.json').write_text(json.dumps({'version':__version__, 'files':entries}, indent=2)+'\n', encoding='utf-8')


def nsis_quote(value):
    return str(value).replace('$', '$$').replace('"', '$\\"')


def generate_uninstall(stage):
    stage = Path(stage)
    files = sorted(p.relative_to(stage) for p in stage.rglob('*') if p.is_file())
    lines = []
    for path in files:
        name = nsis_quote(str(path).replace('/', '\\'))
        lines.extend([f'IfFileExists "$INSTDIR\\app\\{name}" 0 +2', f'Delete "$INSTDIR\\app\\{name}"'])
    lines.append('IfErrors 0 +2')
    lines.append('StrCpy $DeleteFailed "1"')
    dirs = sorted((p.relative_to(stage) for p in stage.rglob('*') if p.is_dir()), key=lambda p:len(p.parts), reverse=True)
    for path in dirs:
        lines.append(f'RMDir "$INSTDIR\\app\\{nsis_quote(str(path).replace(chr(47), chr(92)))}"')
    lines.append('RMDir "$INSTDIR\\app"')
    return '\n'.join(lines)+'\n'


def _build_locked(cache, output, makensis, msiextract, offline=False):
    lock = fetch_inputs(cache, offline)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = output/f'UltraTransfert-{__version__}-Setup-x64-beta.exe'
    if result.exists():
        raise FileExistsError('Installateur existant conservé : choisir un autre dossier de sortie.')
    with tempfile.TemporaryDirectory(prefix='UltraTransfert-installer-') as temp:
        work = Path(temp)
        stage = work/'payload'
        stage_payload(cache, stage, msiextract)
        (work/'uninstall-files.nsh').write_text(generate_uninstall(stage), encoding='utf-8')
        cmd = [makensis, '-V2', '-INPUTCHARSET', 'UTF8',
               '-DAPP_VERSION='+__version__, '-DPAYLOAD='+str(stage), '-DOUTPUT='+str(result),
               '-DDELETE_INCLUDE='+str(work/'uninstall-files.nsh'), str(ROOT/'installer/setup.nsi')]
        subprocess.run(cmd, check=True)
        report = {'version':__version__, 'artifact':result.name, 'sha256':sha256(result),
                  'build':'NSIS cross compilation', 'windows_validated':False,
                  'authenticode_signed':False, 'antivirus_scan':None,
                  'payload_files':len(json.loads((stage/'payload-manifest.json').read_text())['files']),
                  'dependency_inputs':lock['inputs']}
        (output/(result.name+'.build.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        (output/(result.name+'.sha256')).write_text(report['sha256']+'  '+result.name+'\n',encoding='ascii')
    return result


def build(cache, output, makensis, msiextract, offline=False):
    project_lock = ROOT/'.cycle.lock'
    try:
        descriptor = os.open(project_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError('Un cycle détient le verrou du projet. Attendre sa fin.') from None
    try:
        try:
            os.write(descriptor, str(os.getpid()).encode('ascii'))
        finally:
            os.close(descriptor)
        return _build_locked(cache, output, makensis, msiextract, offline)
    finally:
        project_lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT/'.installer-cache')
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    parser.add_argument('--makensis', default='makensis')
    parser.add_argument('--msiextract', default='msiextract')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    print(build(args.cache, args.output, args.makensis, args.msiextract, args.offline))
