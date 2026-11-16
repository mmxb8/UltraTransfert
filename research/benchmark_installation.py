"""Préparation fraîche/réutilisée hors ligne réelle ; option de complément en ligne."""
import argparse
import json
from pathlib import Path
import shutil
import statistics
import tempfile
import time

from prepare_installation import prepare


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--online-check',action='store_true')
    args=parser.parse_args();source=Path(__file__).resolve().parents[1]
    rows=[];online=None
    with tempfile.TemporaryDirectory(prefix='UltraTransfert installation été ') as tmp:
        for i in range(6):
            project=Path(tmp)/str(i);project.mkdir()
            shutil.copytree(source/'ultra',project/'ultra',ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(source/'requirements-sharing.txt',project/'requirements-sharing.txt')
            for mode in ('fresh','reuse'):
                begin=time.perf_counter();result=prepare(project,offline=True);elapsed=time.perf_counter()-begin
                assert result['core_ready'] and not result['sharing_ready'],result
                assert result['core_probe']['resumed_bytes']>0
                rows.append({'method':mode,'round':i,'seconds':elapsed,'report':result})
        if args.online_check:
            # Une seule tentative ; une panne de téléchargement ne bloque pas le moteur.
            begin=time.perf_counter();online=prepare(project,offline=False)
            online['wall_seconds']=time.perf_counter()-begin
            assert online['core_ready'],online
            if online['sharing_ready']:
                import subprocess,os
                python=project/'.venv-run'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
                env=os.environ.copy();env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
                probe="from pathlib import Path; from ultra.share_setup import prepare_share; from ultra.share_restore import load_prepared_share; p=prepare_share('https://localhost:8443',Path('verification-connexion')); assert load_prepared_share(p.directory).certificate_sha256==p.certificate_sha256"
                subprocess.run([str(python),'-c',probe],cwd=project,env=env,check=True,timeout=30)
                online['certificate_prepare_restore_checked']=True
    summary={m:{'median_seconds':statistics.median(r['seconds'] for r in rows if r['method']==m),'min_seconds':min(r['seconds'] for r in rows if r['method']==m),'max_seconds':max(r['seconds'] for r in rows if r['method']==m)} for m in ('fresh','reuse')}
    result={'measurement':'Six fresh and six reused actual POSIX venv preparations without pip/PyPI/cryptography or network request. Includes venv if fresh, interpreter isolation/Tcl probe, real 2-MiB copy/interruption/resume/SHA-256, optional-import probe and report write. Fresh then reuse per pair, not randomized; warm caches and bytecode reuse favor reuse. No Windows/batch/WinGet, visual Tk, EXE, installation without Python or RDP validation. Online optional check is one separately reported real attempt, not a repeated timing comparison.','summary':summary,'raw':rows,'online_check':online}
    (source/'reports/installation-0.3.12.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'summary':summary,'online_check':online},indent=2))


if __name__=='__main__':main()
