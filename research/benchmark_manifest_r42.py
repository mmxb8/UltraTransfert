"""Isolated metadata microbenchmark; NOT end-to-end transfer performance."""
from dataclasses import asdict
import json
from pathlib import Path
import random
import statistics
import time
import tracemalloc
from ultra.engine import Entry

def main():
    entries=[Entry(f'été-{i:04}.txt','file',i%17,1234567890123456789,0o644,(),
                   '1234567890abcdef'*4) for i in range(4096)]
    baseline=lambda:json.dumps([asdict(e) for e in entries],ensure_ascii=False,separators=(',',':')).encode()
    projected=lambda:json.dumps([{n:getattr(e,n) for n in Entry.__dataclass_fields__} for e in entries],
                               ensure_ascii=False,separators=(',',':')).encode()
    assert baseline()==projected()
    methods={'recursive_asdict':baseline,'immutable_fields':projected}
    jobs=[name for name in methods for _ in range(15)];random.Random(77399).shuffle(jobs)
    rows=[]
    for name in jobs:
        start,cpu=time.perf_counter(),time.process_time()
        data=methods[name]()
        rows.append(dict(method=name,seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,bytes=len(data)))
    peaks={}
    for name,fn in methods.items():
        tracemalloc.start();fn();peaks[name]=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    out={'scope':'4096 immutable Entry records, JSON serialization only; no compression, transport, fsync, reconstruction or verification. Not an end-to-end gain.',
         'exact_bytes_equal':True,'rows':rows,'summary':{
           name:dict(median_seconds=statistics.median(r['seconds'] for r in rows if r['method']==name),
                     median_cpu_seconds=statistics.median(r['cpu_seconds'] for r in rows if r['method']==name),
                     peak_python_bytes=peaks[name]) for name in methods}}
    Path('reports/manifest-r42-micro.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out['summary'],indent=2))
if __name__=='__main__':main()
