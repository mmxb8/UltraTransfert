"""Échec d'initialisation réel sous Linux sans DISPLAY, pas un essai Windows."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rounds',type=int,default=5)
    args=parser.parse_args()
    if sys.platform=='win32' or not 1<=args.rounds<=20:parser.error('Linux sans affichage ; 1 à 20 répétitions')
    root=Path(__file__).resolve().parents[1]
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(args.rounds):
            for method in (('previous','current') if i%2==0 else ('current','previous')):
                state=Path(tmp)/f'{i}-{method}'
                script=root/('launch_gui.py' if method=='current' else 'history/v0.3.8/launch_gui.py')
                env=dict(os.environ,DISPLAY='',XDG_STATE_HOME=str(state),PYTHONPATH=str(root))
                start=time.perf_counter()
                # Éviter que le dossier historique partiel masque le paquet courant.
                wrapper="import sys; from pathlib import Path; exec(compile(Path(sys.argv[1]).read_text(),sys.argv[1],'exec'),{'__name__':'__main__'})"
                proc=subprocess.run([sys.executable,'-c',wrapper,str(script)],cwd=root,env=env,capture_output=True,text=True,timeout=15)
                elapsed=time.perf_counter()-start
                logs=list(state.rglob('demarrage-*.log'))
                assert proc.returncode==1
                if method=='current':
                    assert len(logs)==1 and 'TclError' in logs[0].read_text()
                    assert 'ne peut pas ouvrir son interface' in proc.stderr
                else:assert not logs and 'Traceback' in proc.stderr and 'TclError' in proc.stderr
                rows.append({'method':method,'round':i,'seconds':elapsed,'exit_code':proc.returncode,'diagnostic_files':len(logs),'actionable_message':'ne peut pas ouvrir son interface' in proc.stderr})
    summary={m:{'median_seconds':statistics.median(r['seconds'] for r in rows if r['method']==m),'min_seconds':min(r['seconds'] for r in rows if r['method']==m),'max_seconds':max(r['seconds'] for r in rows if r['method']==m)} for m in ('previous','current')}
    report={'measurement':'Real subprocess starts on Linux with DISPLAY empty, alternating order. Previous launcher and current launcher import the same current GUI. Includes process/import/Tk initialization and failure handling; no successful visual launch, EXE, Windows MessageBox, installation, file transfer or RDP. Reliability/overhead comparison, no speed gain claimed.','rounds':args.rounds,'summary':summary,'raw':rows}
    (root/'reports/startup-0.3.9.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
