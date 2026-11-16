"""HTTPS réel sur loopback avec plafond de débit applicatif côté serveur.

Le plafond n'émule pas la latence, les pertes, RDP ni des machines distinctes.
Comparaison de codecs ET du sélecteur avec temps de copie/vérification réel.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import secrets
import statistics
import struct
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch

from ultra.compression import ZSTD, frame
from ultra.engine import LocalSource, Options, Transfer, digest
from ultra.network import RemoteSource, make_server


class MeteredWriter:
    def __init__(self, output, rate, metrics, lock):
        self.output, self.rate, self.metrics, self.lock = output, rate, metrics, lock

    def write(self, data):
        # Attendre par morceau : débit plafonné même pour un gros write brut.
        started=time.perf_counter()
        sent=0
        for offset in range(0,len(data),16384):
            block=data[offset:offset+16384]
            self.output.write(block)
            sent+=len(block)
            delay=sent/self.rate-(time.perf_counter()-started)
            if delay>0:time.sleep(delay)
        with self.lock:self.metrics['http_plaintext_bytes']+=sent
        return sent

    def __getattr__(self,name):
        return getattr(self.output,name)


class FixedEncoder:
    def __init__(self, codec, width):
        self.codec,self.width=codec,width
        self.searches=self.reused=0

    def encode(self,data):
        return frame(data,self.codec,self.width)


def datasets():
    size=8*1024*1024+123
    rng=random.Random(482711)
    signal=b''.join(struct.pack('<f',math.sin(i*.001)+.0001*(i%7)) for i in range(size//4))
    noise=rng.randbytes(size)
    rows=b''.join(json.dumps({'event':i,'service':'inventory','status':'ok','customer':i%71}).encode()+b'\n' for i in range(70000))
    # Changement de nature au milieu du flux : force la sortie d'une recette.
    mixed=(rows*(size//len(rows)+1))[:4*1024*1024]+noise[:4*1024*1024+123]
    return {'float32_signal_synthetic':signal,
            'logs_then_random_synthetic':mixed,
            'gzip_of_pseudo_random':gzip.compress(noise,compresslevel=1,mtime=0)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--mbps',type=float,nargs='+',default=[50])
    parser.add_argument('--reference',type=Path,help='Ancien module compression.py pour comparaison sur le même banc')
    parser.add_argument('--output',type=Path,default=Path('reports/https-compression.json'))
    parser.add_argument('--selection-pruning',action='store_true',help='Activer le prototype sur ultra, sans modifier la référence')
    args=parser.parse_args()
    if not 1<=args.rounds<=9 or any(not math.isfinite(r) or r<=0 for r in args.mbps):
        parser.error('1–9 répétitions et débits positifs finis requis')
    rows=[]
    methods=['none','gzip','ultra']+(['zstd1','zstd1-shuffle4','zstd3','zstd3-shuffle4'] if ZSTD else [])
    reference=None
    if args.reference:
        spec=importlib.util.spec_from_file_location('reference_compression',args.reference)
        reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
        methods.append('ultra-reference')
    inputs=datasets()
    with tempfile.TemporaryDirectory(prefix='ultra-https-compression-') as tmp:
        base=Path(tmp);cert,key=base/'cert.pem',base/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        jobs=[(name,method,rate,i) for name in inputs for method in methods for rate in args.mbps for i in range(args.rounds)]
        random.Random(821).shuffle(jobs)
        for number,(name,method,rate,iteration) in enumerate(jobs):
            root=base/str(number);root.mkdir();source=root/'source';source.mkdir()
            data=inputs[name]
            (source/'données.bin').write_bytes(data)
            (source/'vide').write_bytes(b'');(source/'dossier vide').mkdir()
            expected=digest(source/'données.bin')
            token=secrets.token_urlsafe(48)
            mode=method if method in ('none','gzip') else 'ultra'
            started=time.perf_counter()
            server=make_server(LocalSource(source),('127.0.0.1',0),cert,key,token,mode,link_mbps=rate,selection_pruning=args.selection_pruning and method=='ultra')
            preparation=time.perf_counter()-started
            metrics={'http_plaintext_bytes':0};lock=threading.Lock()
            parent=server.RequestHandlerClass
            class MeasuredHandler(parent):
                def setup(self):
                    super().setup()
                    self.wfile=MeteredWriter(self.wfile,rate*1e6/8,metrics,lock)
            server.RequestHandlerClass=MeasuredHandler
            thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
            def fixed_encoder(*unused):
                return FixedEncoder('zstd1' if method.startswith('zstd1') else 'zstd3',4 if method.endswith('-shuffle4') else 1)
            try:
                from contextlib import nullcontext
                if method=='ultra-reference':
                    context=patch('ultra.network.AdaptiveEncoder',reference.AdaptiveEncoder)
                elif method.startswith('zstd'):
                    context=patch('ultra.network.AdaptiveEncoder',side_effect=fixed_encoder)
                else:
                    context=nullcontext()
                with context:
                    started=time.perf_counter()
                    remote=RemoteSource(f'https://localhost:{server.server_port}',token,cert,mode)
                    result=Transfer(remote,root/'destination',Options(workers=1)).run()
                    elapsed=time.perf_counter()-started
                if result.errors:raise RuntimeError(result.errors)
                if digest(root/'destination'/'données.bin')!=expected:raise RuntimeError('SHA-256 indépendant différent')
                row={'dataset':name,'method':method,'link_mbps':rate,'round':iteration,
                     'input_bytes':len(data),'client_seconds':elapsed,'source_preparation_seconds':preparation,
                     'total_seconds':preparation+elapsed,
                     'http_plaintext_bytes':metrics['http_plaintext_bytes'],
                     'server_metrics':dict(server.transfer_metrics),'independent_sha256':expected}
                rows.append(row)
                print(json.dumps({k:row[k] for k in ('dataset','method','link_mbps','round','client_seconds','http_plaintext_bytes')}),flush=True)
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)
            import shutil
            shutil.rmtree(root)
    summary=[]
    for name in inputs:
        for rate in args.mbps:
            for method in methods:
                sample=[r for r in rows if r['dataset']==name and r['link_mbps']==rate and r['method']==method]
                summary.append({'dataset':name,'link_mbps':rate,'method':method,
                                'median_seconds':statistics.median(r['client_seconds'] for r in sample),
                                'median_total_seconds':statistics.median(r['total_seconds'] for r in sample),
                                'min_total_seconds':min(r['total_seconds'] for r in sample),
                                'max_total_seconds':max(r['total_seconds'] for r in sample),
                                'min_seconds':min(r['client_seconds'] for r in sample),
                                'max_seconds':max(r['client_seconds'] for r in sample),
                                'median_http_plaintext_bytes':statistics.median(r['http_plaintext_bytes'] for r in sample)})
    report={'rounds':args.rounds,'zstd_version':ZSTD.version if ZSTD else None,
            'selection_pruning':args.selection_pruning,
            'reference':str(args.reference) if args.reference else None,
            'reference_sha256':hashlib.sha256(args.reference.read_bytes()).hexdigest() if args.reference else None,
            'total_scope':'total_seconds = source_preparation_seconds + client_seconds. Includes source inventory/hashing, server TLS configuration, client manifest/TLS, selection, codecs, reconstruction, write/fsync and engine verification. No dictionary. Excludes creation of synthetic inputs, common fixture certificate generation (not timed), server shutdown, extra independent SHA-256, installation and human actions.',
            'measurement':'Actual HTTPS loopback copies, server application output paced to configured Mbit/s per connection in 16-KiB slices; HTTP bytes counted before TLS encryption. Randomized jobs; warm filesystem caches. Client timing includes manifest/TLS, codec selection, encoding/decoding, destination writes/fsync and full engine integrity checks. Source preparation reported separately; extra independent SHA-256 excluded from timing. No RTT/loss emulation, RDP, USB, distinct machines or cold caches. Three synthetic ~8-MiB datasets. Fixed Zstd baselines use the same verified block frames, with width 1 or width 4; none/gzip use existing HTTP format. Not a market-wide comparison or a novelty claim.',
            'summary':summary,'raw':rows}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
