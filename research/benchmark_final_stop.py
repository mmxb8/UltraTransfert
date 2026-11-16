"""Arrêt au début de l'inventaire final : référence et moteur actuel réels."""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile
import threading
import time

import ultra.engine as current


def main():
    root=Path(__file__).resolve().parent.parent
    name='ultra.engine_reference_final_stop'
    spec=importlib.util.spec_from_file_location(name,root/'history/v0.3.16/ultra/engine.py')
    old=importlib.util.module_from_spec(spec);sys.modules[name]=old;spec.loader.exec_module(old)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='ultra-final-stop-') as tmp:
        for count in (0,2000):
            src=Path(tmp)/f'source-{count}';src.mkdir();(src/'dossier vide').mkdir()
            for i in range(count):(src/f'été_日本語_{i}').write_bytes(b'exact')
            for repeat in range(3):
                for version in (('old','new') if repeat%2==0 else ('new','old')):
                    module=old if version=='old' else current
                    dst=Path(tmp)/f'dest-{count}-{repeat}-{version}';cancel=threading.Event();state={}
                    def phase(text):
                        if text.startswith('Vérification finale'):
                            state['requested_at']=time.perf_counter();cancel.set()
                    source=module.LocalSource(src)
                    started=time.perf_counter()
                    result=module.Transfer(source,dst,module.Options(workers=1),cancel=cancel,phase=phase).run()
                    ended=time.perf_counter()
                    if version=='new':assert result.errors
                    if version=='old' and count==0:assert not result.errors
                    assert not (dst/module.STATE/'lock').exists()
                    # Contrôle indépendant après chrono, y compris pour les résultats interrompus.
                    files={p.name for p in dst.iterdir() if p.is_file()}
                    assert files=={p.name for p in src.iterdir() if p.is_file()}
                    assert (dst/'dossier vide').is_dir()
                    assert all(p.read_bytes()==b'exact' and (dst/p.name).read_bytes()==b'exact' for p in src.iterdir() if p.is_file())
                    rows.append(dict(files=count,repeat=repeat,version=version,seconds=ended-started,
                                     after_stop_seconds=ended-state['requested_at'],errors=result.errors,
                                     copied=result.copied))
    summary=[]
    for count in (0,2000):
        for version in ('old','new'):
            selected=[r for r in rows if r['files']==count and r['version']==version]
            values=[r['after_stop_seconds'] for r in selected]
            summary.append(dict(files=count,version=version,median_after_stop_seconds=statistics.median(values),
                                min_seconds=min(values),max_seconds=max(values),
                                success_after_stop_count=sum(not r['errors'] for r in selected)))
    report=dict(scope='Actual local Linux copies; synthetic tiny Unicode files and empty directory; three alternating repetitions per variant and size. Stop at final-inventory phase boundary. Time to engine return includes report/journal cleanup. Fixtures and independent byte/inventory checks excluded. Warm caches, no GUI/Windows/RDP/network or physical disk throughput claim.',rows=rows,summary=summary)
    (root/'reports/final-stop-0.3.17.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
