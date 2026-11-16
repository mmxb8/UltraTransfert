"""Ancien/nouveau sélecteur et recettes fixes, CPU mesuré, réseau estimé seulement."""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import statistics
import time

from ultra import compression as c
from research.benchmark_compression import datasets


def main():
    reference=Path('history/v0.3.12/ultra/compression.py')
    spec=importlib.util.spec_from_file_location('reference_compression',reference)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    inputs=datasets();methods=['previous','current','raw','zlib1']+(['zstd1','zstd3','zstd3-shuffle4'] if c.ZSTD else [])
    jobs=[(name,method,rate,i) for name in inputs for method in methods for rate in (50,1000) for i in range(7)]
    random.Random(336).shuffle(jobs);rows=[]
    for name,method,rate,iteration in jobs:
        data=inputs[name];begin=time.perf_counter()
        if method in ('previous','current'):
            module=old if method=='previous' else c
            encoded,details=module.adaptive_frame(data,rate,**({'prune':True} if method=='current' else {}))
        else:
            encoded=c.frame(data,'zstd3' if method=='zstd3-shuffle4' else method,4 if method=='zstd3-shuffle4' else 1);details={}
        encoding=time.perf_counter()-begin
        begin=time.perf_counter();decoded=c.unframe(encoded);decoding=time.perf_counter()-begin
        assert decoded==data
        rows.append({'dataset':name,'method':method,'round':iteration,'link_mbps':rate,'input_bytes':len(data),'wire_frame_bytes':len(encoded),'encode_seconds':encoding,'decode_seconds':decoding,'cpu_seconds':encoding+decoding,'selection_seconds':details.get('selection_seconds',0),'pruned_candidates':sum(bool(x.get('pruned')) for x in details.get('candidates',[])),'selected':details.get('selected'),'estimated_serial_seconds':encoding+decoding+len(encoded)/(rate*1e6/8),'sha256':hashlib.sha256(decoded).hexdigest()})
    summary=[]
    for name in inputs:
        for rate in (50,1000):
            for method in methods:
                group=[r for r in rows if (r['dataset'],r['link_mbps'],r['method'])==(name,rate,method)]
                summary.append({'dataset':name,'link_mbps':rate,'method':method,'median_cpu_seconds':statistics.median(r['cpu_seconds'] for r in group),'median_selection_seconds':statistics.median(r['selection_seconds'] for r in group),'median_estimated_serial_seconds':statistics.median(r['estimated_serial_seconds'] for r in group),'min_cpu_seconds':min(r['cpu_seconds'] for r in group),'max_cpu_seconds':max(r['cpu_seconds'] for r in group),'median_pruned_candidates':statistics.median(r['pruned_candidates'] for r in group)})
    report={'measurement':'Six synthetic ~2-MiB blocks, seven repetitions per variant in randomized order; actual encode/search/frame/hash and receiver reconstruction/hash time. Serial transfer time is an ESTIMATE at 50/1000 Mbit/s, not a network run; no disk, TLS, RTT, Windows or RDP. Fixed raw/zlib1/Zstd1/3 and shuffle4 when available, not all market codecs. Separate actual HTTPS benchmark includes preparation/transport/write/verification.','reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'zstd_version':c.ZSTD.version if c.ZSTD else None,'summary':summary,'raw':rows}
    Path('reports/selection-0.3.13.json').write_text(json.dumps(report,indent=2))
    for row in summary:
        if row['method'] in ('previous','current'):print(json.dumps(row))


if __name__=='__main__':main()
