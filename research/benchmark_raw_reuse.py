"""CPU réel du chemin brut réutilisé ; aucun réseau ni débit disque mesuré."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import statistics
import time

from ultra import compression as current


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rounds',type=int,default=15)
    parser.add_argument('--reference',type=Path,default=Path('history/v0.3.7/ultra/compression.py'))
    parser.add_argument('--output',type=Path,default=Path('reports/raw-reuse-0.3.8.json'))
    args=parser.parse_args()
    if not 3<=args.rounds<=99:parser.error('3 à 99 répétitions requises')
    spec=importlib.util.spec_from_file_location('reference_compression',args.reference)
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    modules={'previous':previous,'current':current}
    noise=random.Random(8872).randbytes(current.MAX_BLOCK)
    inputs={'pseudo_random':noise,'gzip_of_pseudo_random':gzip.compress(noise,compresslevel=1,mtime=0)[:current.MAX_BLOCK]}
    rows=[]
    # État imposé : bloc suivant une décision brute déjà obtenue. La recherche
    # initiale n'est PAS mesurée ici ; elle l'est dans le banc HTTPS complet.
    jobs=[(name,method,i) for name in inputs for method in modules for i in range(args.rounds+2)]
    random.Random(227).shuffle(jobs)
    for name,method,iteration in jobs:
        module=modules[method];data=inputs[name]
        encoder=module.AdaptiveEncoder(1000)
        encoder.recipe=('raw',1);encoder.blocks=1
        begin=time.perf_counter()
        encoded=encoder.encode(data)
        encoding=time.perf_counter()-begin
        begin=time.perf_counter();restored=module.unframe(encoded)
        decoding=time.perf_counter()-begin
        if restored!=data or encoded!=current.frame(data):raise RuntimeError('Octets/trame différents')
        if iteration>=2:
            rows.append({'dataset':name,'method':method,'round':iteration-2,'input_bytes':len(data),
                         'frame_bytes':len(encoded),'encoding_seconds':encoding,'decoding_seconds':decoding,
                         'total_seconds':encoding+decoding,'sha256':hashlib.sha256(restored).hexdigest()})
    summary=[]
    for name in inputs:
        for method in modules:
            sample=[r for r in rows if r['dataset']==name and r['method']==method]
            summary.append({'dataset':name,'method':method,
                            'median_encoding_seconds':statistics.median(r['encoding_seconds'] for r in sample),
                            'median_total_seconds':statistics.median(r['total_seconds'] for r in sample),
                            'min_total_seconds':min(r['total_seconds'] for r in sample),
                            'max_total_seconds':max(r['total_seconds'] for r in sample)})
    report={'rounds':args.rounds,'python':platform.python_version(),'platform':platform.platform(),
            'zstd_version':current.ZSTD.version if current.ZSTD else None,
            'reference':str(args.reference),'reference_sha256':hashlib.sha256(args.reference.read_bytes()).hexdigest(),
            'measurement':'Actual CPU wall time, warm 4-MiB synthetic blocks. State forced to raw recipe, block number 1; includes next-block compressibility probe, framing, encoding and receiver reconstruction/SHA-256. Initial selection, TLS, transport, disk, setup, extra equality/hash checks and human actions excluded. First two indexed rounds per variant excluded, jobs randomized. This isolates the affected steady-state path, NOT total file-transfer speed. Full initial selection/preparation included separately in HTTPS benchmark.',
            'summary':summary,'raw':rows}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
