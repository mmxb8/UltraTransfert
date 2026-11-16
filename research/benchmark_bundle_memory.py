"""Isolated RSS and Python-traced peak, raw 32 MiB bundle; no network."""
import argparse
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from research.smallfile_bundle import pack


def main():
    p=argparse.ArgumentParser();p.add_argument('--child',nargs=2);a=p.parse_args()
    if a.child:
        revision,path=a.child
        if revision=='R4.0': from research.smallfile_bundle_r40 import BundleSource
        else: from research.smallfile_bundle import BundleSource
        tracemalloc.start(); start=time.perf_counter();cpu=time.process_time()
        source=BundleSource(path)
        elapsed=time.perf_counter()-start;cpu=time.process_time()-cpu
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        rss=int(next(l.split()[1] for l in Path('/proc/self/status').read_text().splitlines() if l.startswith('VmHWM:')))
        # All bytes hashed by parser; materialize one file independently.
        import hashlib
        for e in source.entries:
            if e.kind=='file':
                with source.open(e) as stream: assert hashlib.sha256(stream.read()).hexdigest()==e.sha256
        print(json.dumps(dict(revision=revision,seconds=elapsed,cpu_seconds=cpu,peak_python_bytes=peak,max_rss_kib=rss)))
        return
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);src=root/'src';src.mkdir();rng=random.Random(8551)
        for i in range(512): (src/f'{i:04}.bin').write_bytes(rng.randbytes(65536))
        path=root/'large.utb';pack(src,path,codec='raw')
        jobs=['R4.0','R4.1']*7;random.Random(999).shuffle(jobs);rows=[]
        for revision in jobs:
            rows.append(json.loads(subprocess.check_output([sys.executable,'-m','research.benchmark_bundle_memory','--child',revision,str(path)],text=True)))
        summary=[dict(revision=rev,**{k:statistics.median(r[k] for r in rows if r['revision']==rev) for k in ('seconds','cpu_seconds','peak_python_bytes','max_rss_kib')}) for rev in ('R4.0','R4.1')]
        Path('reports/bundle-r4-memory.json').write_text(json.dumps(dict(scope='Untimed prepacked 32 MiB / 512 distinct seeded pseudo-random files. Decode/group SHA256/file SHA256 and memory index construction included, no network/engine/destination write. Tracemalloc timing adds overhead. RSS process high water includes Python imports/native allocations, Linux isolated processes, 7 repetitions per revision, warm caches.',summary=summary,raw=rows),indent=2))
        print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
