"""Producer-only bounded-memory experiment; not a transfer benchmark."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from research.smallfile_bundle import pack, BundleSource
from research.smallfile_bundle_r42 import pack as old_pack

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--child',nargs=4)
    p.add_argument('--rounds',type=int,default=7)
    a=p.parse_args()
    if a.child:
        revision,source,output,codec=a.child
        kwargs={'spool':True} if revision=='R43-spool' else {}
        fn=pack if kwargs else old_pack
        tracemalloc.start();start=time.perf_counter();cpu=time.process_time()
        metrics=fn(source,output,codec=codec,manifest_codec='deflate1',**kwargs)
        seconds=time.perf_counter()-start;cpu=time.process_time()-cpu
        peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        rss=int(next(l.split()[1] for l in Path('/proc/self/status').read_text().splitlines() if l.startswith('VmHWM:')))
        # Extra verification deliberately outside all above measurements.
        source_impl=BundleSource(output)
        for entry in source_impl.entries:
            if entry.kind=='file':
                with source_impl.open(entry) as stream:
                    assert stream.read()==(Path(source)/entry.path).read_bytes()
        print(json.dumps(dict(revision=revision,codec=codec,seconds=seconds,cpu_seconds=cpu,
          peak_python_bytes=peak,max_rss_kib=rss,sha256=hashlib.sha256(Path(output).read_bytes()).hexdigest(),
          verified=True,**metrics)))
        return
    if not 1<=a.rounds<=9: p.error('1 to 9 rounds')
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for name in ('random','repeated'):
            src=root/name;src.mkdir();rng=random.Random(737712)
            for i in range(512):
                data=rng.randbytes(65536) if name=='random' else (f'log-item-{i%17:02}\n'.encode()*6000)[:65536]
                # Pad to the same size; repeated corpus contains structured text.
                (src/f'f-{i:04}').write_bytes(data.ljust(65536,b' '))
        jobs=[(name,codec,revision,i) for name in ('random','repeated')
              for codec in ('raw','auto') for revision in ('R42','R43-spool') for i in range(a.rounds)]
        random.Random(731991).shuffle(jobs)
        for j,(name,codec,revision,i) in enumerate(jobs):
            out=root/f'output-{j}'
            row=json.loads(subprocess.check_output([sys.executable,'-m','research.benchmark_pack_memory_r43',
                            '--child',revision,str(root/name),str(out),codec],text=True))
            row.update(dataset=name,round=i);rows.append(row);out.unlink()
        for name in ('random','repeated'):
            for codec in ('raw','auto'):
                assert len({v['sha256'] for v in rows if v['dataset']==name and v['codec']==codec})==1
    summary=[]
    for name in ('random','repeated'):
        for codec in ('raw','auto'):
            for rev in ('R42','R43-spool'):
                selected=[v for v in rows if (v['dataset'],v['codec'],v['revision'])==(name,codec,rev)]
                summary.append(dict(dataset=name,codec=codec,revision=rev,
                  **{'median_'+k:statistics.median(v[k] for v in selected) for k in
                     ('seconds','cpu_seconds','peak_python_bytes','max_rss_kib','container_bytes')},
                  min_seconds=min(v['seconds'] for v in selected),max_seconds=max(v['seconds'] for v in selected)))
    result=dict(scope='Producer-only 32 MiB/512 files per corpus. Warm caches; private scratch file in same local directory. Includes source inventory/reads/hash/metadata, compression, spool write/reread when enabled, final container fsync/publication and stability checks. Excludes fixtures, interpreter imports, network and recipient reconstruction. Tracemalloc adds timing overhead. RSS sampled before untimed verification; isolated Linux processes. Each container independently parsed and all file bytes compared, outputs exactly equal per corpus/codec.',
                rounds=a.rounds,summary=summary,raw=rows)
    Path('reports/bundle-r43-producer-memory.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
