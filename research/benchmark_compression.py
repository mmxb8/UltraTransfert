"""Comparaison synthétique : taille ET temps CPU, durée réseau seulement estimée."""
from dataclasses import asdict
import gzip
import importlib.util
import json
import math
from pathlib import Path
import platform
import random
import statistics
import struct
import time

from research.compression import ZSTD,adaptive_frame,codecs,frame,unframe


def datasets():
    size=2*1024*1024
    rng=random.Random(33685)
    noise=rng.randbytes(size)
    logs=b''.join(json.dumps({'event':i,'service':'inventory','status':'ok','customer_id':i%71,'message':'synchronisation completed'}).encode()+b'\n' for i in range(17000))
    integers=b''.join(struct.pack('<I',i) for i in range(size//4))
    floats=b''.join(struct.pack('<f',math.sin(i*.001)+.0001*(i%7)) for i in range(size//4))
    return {'json_logs_synthetic':logs[:size], 'uint32_counter_synthetic':integers,
            'float32_signal_synthetic':floats, 'pseudo_random':noise,
            'gzip_of_pseudo_random':gzip.compress(noise,compresslevel=1,mtime=0),
            'mixed_logs_and_random':logs[:size//2]+noise[:size//2]}


def main():
    rounds=5
    rows=[]
    for name,data in datasets().items():
        for rate in (10,1000):
            jobs=[(method,i) for method in ('raw','zlib1','zstd1','zstd3','adaptive') if method in codecs() or method=='adaptive' for i in range(rounds)]
            random.Random(717).shuffle(jobs)
            for method,iteration in jobs:
                begin=time.perf_counter()
                if method=='adaptive':
                    encoded,details=adaptive_frame(data,rate)
                else:
                    encoded=frame(data,method,1);details={}
                enc=time.perf_counter()-begin
                begin=time.perf_counter();decoded=unframe(encoded);dec=time.perf_counter()-begin
                if decoded!=data:raise RuntimeError('Roundtrip mismatch')
                estimate=enc+dec+len(encoded)/(rate*1e6/8)
                rows.append({'dataset':name,'link_mbps':rate,'method':method,'round':iteration,
                             'input_bytes':len(data),'encoded_bytes':len(encoded),
                             'encode_seconds':enc,'decode_seconds':dec,
                             'estimated_total_seconds':estimate,'details':details})
    summary=[]
    for name in datasets():
        for rate in (10,1000):
            methods=sorted({r['method'] for r in rows})
            for method in methods:
                sample=[r for r in rows if r['dataset']==name and r['link_mbps']==rate and r['method']==method]
                summary.append({'dataset':name,'link_mbps':rate,'method':method,
                                'median_encoded_bytes':statistics.median(r['encoded_bytes'] for r in sample),
                                'median_encode_seconds':statistics.median(r['encode_seconds'] for r in sample),
                                'median_decode_seconds':statistics.median(r['decode_seconds'] for r in sample),
                                'median_estimated_total_seconds':statistics.median(r['estimated_total_seconds'] for r in sample),
                                'input_bytes':sample[0]['input_bytes']})
    report={'python':platform.python_version(),'platform':platform.platform(),'zstd_system_version':ZSTD.version if ZSTD else None,
            'rounds':rounds,'measurement':'Synthetic 2-MiB-scale blocks, randomized order, five repetitions. Encoding time includes adaptive search overhead, framing and hash; decoding includes reverse transform and SHA-256. No actual network, RDP, disk write, pipeline overlap or reference deduplication is measured. Estimated serial duration = actual measured encode + actual measured decode + frame bytes / configured link bandwidth. Small blocks and synthetic data do not establish production performance or novelty. Baselines are zlib1 and system Zstandard levels 1 and 3; no comparison against all existing codecs.',
            'summary':summary,'raw':rows}
    Path('reports/compression-lab.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    for name in datasets():
        rate=10
        group={s['method']:s for s in summary if s['dataset']==name and s['link_mbps']==rate}
        adaptive=group['adaptive'];baseline=group.get('zstd3',group['zlib1'])
        print(json.dumps({'dataset':name,'link_mbps':rate,
            'adaptive_encoded_bytes':adaptive['median_encoded_bytes'],
            'baseline_encoded_bytes':baseline['median_encoded_bytes'],
            'adaptive_estimated_seconds':adaptive['median_estimated_total_seconds'],
            'baseline_estimated_seconds':baseline['median_estimated_total_seconds'],
            'estimated_gain_percent':100*(1-adaptive['median_estimated_total_seconds']/baseline['median_estimated_total_seconds'])}))


if __name__=='__main__':main()
