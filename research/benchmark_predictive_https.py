"""Research-only HTTPS adapter; UTCP1 is NOT negotiated by released clients.

Patches are scoped to this harness and restored after each copy. Published
application code and the 0.4.0 installer remain untouched.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import random
import secrets
import shutil
import statistics
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch

from research.benchmark_https_compression import MeteredWriter
from research.benchmark_predictive import Method, datasets
from ultra.engine import LocalSource, Options, Transfer, digest
from ultra.network import RemoteSource, make_server


class Encoder:
    def __init__(self,method,rate):
        self.method=Method(method,rate)
        self.searches=self.reused=0

    def encode(self,data):
        encoded=self.method.encode(data)
        if self.method.encoder:
            self.searches=self.method.encoder.searches
            self.reused=self.method.encoder.reused
        return encoded


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cpu-report',type=Path,default=Path('reports/predictive-cpu.json'))
    p.add_argument('--rounds',type=int,default=5)
    p.add_argument('--extra-methods',nargs='*',default=[])
    p.add_argument('--only',nargs='+',default=None)
    p.add_argument('--mbps',type=float,nargs='+',default=[50,1000])
    p.add_argument('--output',type=Path,default=Path('reports/predictive-https.json'))
    a=p.parse_args()
    if not 1<=a.rounds<=20 or any(r<=0 for r in a.mbps):p.error('Invalid rounds/rate')
    cpu=json.loads(a.cpu_report.read_text())
    inputs=datasets()
    if {n:hashlib.sha256(d).hexdigest() for n,d in inputs.items()} != cpu['dataset_sha256']:
        raise ValueError('Inputs differ from the CPU reference report; rerun CPU report on this host')
    if a.only:
        inputs={name:inputs[name] for name in a.only}
    references={}
    for name in inputs:
        for rate in a.mbps:
            rows=[r for r in cpu['summary'] if r['dataset']==name and r['link_mbps']==rate
                  and r['method'] not in ('predictive','predictive_initial','ultra_0.4.0','fixed-subtract4-zstd3','budget_R2')]
            if not rows:raise ValueError('CPU report missing requested rate')
            references[name,rate]=min(rows,key=lambda r:r['median_estimated_serial_seconds'])['method']
    jobs=[]
    for name in inputs:
        for rate in a.mbps:
            methods=sorted({'raw','ultra_0.4.0','predictive',references[name,rate],*a.extra_methods})
            jobs.extend((name,rate,m,i) for m in methods for i in range(a.rounds))
    random.Random(19341).shuffle(jobs)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='ultra-predictive-https-') as tmp:
        base=Path(tmp);cert=base/'cert.pem';key=base/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),
                        '-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for number,(name,rate,method,iteration) in enumerate(jobs):
            root=base/str(number);source=root/'source';source.mkdir(parents=True)
            data=inputs[name]
            (source/'données.bin').write_bytes(data)
            (source/'vide').write_bytes(b'');(source/'dossier vide').mkdir()
            token=secrets.token_urlsafe(48)
            mode='none' if method=='raw' else 'ultra'
            cpu_start=time.process_time();started=time.perf_counter()
            server=make_server(LocalSource(source),('127.0.0.1',0),cert,key,token,mode,link_mbps=rate)
            prep=time.perf_counter()-started
            metrics={'http_plaintext_bytes':0};lock=threading.Lock();parent=server.RequestHandlerClass
            class Measured(parent):
                def setup(self):
                    super().setup()
                    self.wfile=MeteredWriter(self.wfile,rate*1e6/8,metrics,lock)
            server.RequestHandlerClass=Measured
            thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
            try:
                with ExitStack() as stack:
                    if method in ('budget_R3','raw_blocks_R3','utcp-raw_R3','utcp-subtract4_R3'):
                        from research.stream_reader_r3 import LeanBlockReader
                        stack.enter_context(patch('ultra.network.BlockReader',LeanBlockReader))
                    if method not in ('raw','ultra_0.4.0'):
                        stack.enter_context(patch('ultra.network.AdaptiveEncoder',side_effect=lambda *args,**kw:Encoder(method,rate)))
                        decoder=Method(method,rate).decode
                        if method in ('budget_R3','utcp-raw_R3','utcp-subtract4_R3'):
                            from research.stream_reader_r3 import raw_view_unframe
                            decoder=raw_view_unframe
                        stack.enter_context(patch('ultra.blockstream.unframe',decoder))
                    start=time.perf_counter()
                    remote=RemoteSource(f'https://localhost:{server.server_port}',token,cert,mode)
                    result=Transfer(remote,root/'destination',Options(workers=1)).run()
                    elapsed=time.perf_counter()-start
                cpu_elapsed=time.process_time()-cpu_start
                if result.errors:raise RuntimeError(result.errors)
                expected=hashlib.sha256(data).hexdigest()
                if digest(root/'destination'/'données.bin')!=expected:raise RuntimeError('Independent digest mismatch')
                row={'dataset':name,'method':method,'reference_for_dataset':references[name,rate],
                     'link_mbps':rate,'round':iteration,'input_bytes':len(data),'source_preparation_seconds':prep,
                     'client_seconds':elapsed,'total_seconds':prep+elapsed,'cpu_seconds':cpu_elapsed,
                     'http_plaintext_bytes':metrics['http_plaintext_bytes'],
                     'server_metrics':dict(server.transfer_metrics),'sha256':expected}
                rows.append(row)
                print(json.dumps({k:row[k] for k in ('dataset','method','link_mbps','round','total_seconds','http_plaintext_bytes')}),flush=True)
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)
            shutil.rmtree(root)
    summary=[]
    for name in inputs:
        for rate in a.mbps:
            for method in sorted({r['method'] for r in rows if r['dataset']==name and r['link_mbps']==rate}):
                sample=[r for r in rows if r['dataset']==name and r['link_mbps']==rate and r['method']==method]
                row={'dataset':name,'method':method,'link_mbps':rate,'input_bytes':len(inputs[name])}
                for field in ('total_seconds','client_seconds','source_preparation_seconds','cpu_seconds','http_plaintext_bytes'):
                    row['median_'+field]=statistics.median(r[field] for r in sample)
                row['min_total_seconds']=min(r['total_seconds'] for r in sample)
                row['max_total_seconds']=max(r['total_seconds'] for r in sample)
                summary.append(row)
    a.output.write_text(json.dumps({'rounds':a.rounds,
        'scope':'Actual authenticated TLS loopback, application writer paced per connection in 16-KiB slices. Includes source inventory/SHA256/TLS setup plus client manifest/TLS, codec selection, encoding, reconstruction, destination write/fsync and all engine checks. Excludes input generation, common certificate fixture generation, server shutdown, extra independent hash. CPU includes sender and receiver in one process. Warm caches, single file worker. No RTT/loss emulation, distinct hosts, Windows, RDP, USB or native pipeline. Selected reference has oracle knowledge from preliminary CPU benchmark per dataset/rate; this is not best of all market products. Nonstandard research frames are injected by scoped test patches, not shipped as a negotiated application feature. HTTP plaintext bytes include headers before TLS, not actual encrypted wire bytes.',
        'dataset_sha256':{n:cpu['dataset_sha256'][n] for n in inputs},'reference_cpu_report':str(a.cpu_report),
        'summary':summary,'raw':rows},indent=2),encoding='utf8')


if __name__=='__main__':main()
