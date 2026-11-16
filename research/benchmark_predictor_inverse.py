"""Compare two exact inverses, randomized jobs, no concurrent benchmarks."""
import hashlib
import json
from pathlib import Path
import random
import statistics
import time

from research.predictive_compression import MAX_BLOCK, predict


def main():
    rng=random.Random(442918)
    inputs={n:rng.randbytes(n) for n in (1048576,MAX_BLOCK)}
    encoded={(n,w):predict(d,w,'subtract') for n,d in inputs.items() for w in (4,8,16)}
    jobs=[(n,w,m,i) for n in inputs for w in (4,8,16) for m in ('doubling','division') for i in range(9)]
    rng.shuffle(jobs)
    raw=[]
    for n,w,m,i in jobs:
        start=time.perf_counter();cpu=time.process_time()
        restored=predict(encoded[n,w],w,'subtract',True,inversion=m)
        cpu=time.process_time()-cpu;elapsed=time.perf_counter()-start
        assert restored==inputs[n]
        raw.append({'bytes':n,'width':w,'method':m,'round':i,'seconds':elapsed,'cpu_seconds':cpu})
    summary=[]
    for n in inputs:
        for w in (4,8,16):
            for m in ('doubling','division'):
                rows=[r for r in raw if r['bytes']==n and r['width']==w and r['method']==m]
                summary.append({'bytes':n,'width':w,'method':m,
                                'median_seconds':statistics.median(r['seconds'] for r in rows),
                                'min_seconds':min(r['seconds'] for r in rows),
                                'max_seconds':max(r['seconds'] for r in rows)})
    Path('reports/predictor-inverse.json').write_text(json.dumps({
        'scope':'Only predictor inversion on pseudorandom aligned bytes, nine randomized repeats per combination. Includes bigint construction/output. Excludes transform encoding, codec, network and hashing; correctness compared outside timing. This is a microbenchmark, not transfer speed. Pure Python stdlib bigint operations, no new dependency.',
        'sha256':{n:hashlib.sha256(d).hexdigest() for n,d in inputs.items()},'summary':summary,'raw':raw},indent=2))
    for n in inputs:
        rows={r['method']:r for r in summary if r['bytes']==n and r['width']==4}
        print(n,rows)


if __name__=='__main__':main()
