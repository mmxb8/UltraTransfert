"""R4 bounded small-file experiment, actual TLS loopback, isolated processes."""
import argparse
from contextlib import ExitStack
import gzip
import hashlib
import json
from pathlib import Path
import platform
import random
import secrets
import shutil
import statistics
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
from unittest.mock import patch

from research.smallfile_bundle import BundleSource, pack
from research.benchmark_https_compression import MeteredWriter
from research.benchmark_predictive import Method
from ultra.engine import LocalSource, Options, Transfer, digest, inventory
from ultra.network import RemoteSource, make_server


class Encoder:
    def __init__(self, method):
        self.method=Method(method,50); self.searches=self.reused=0
    def encode(self,data): return self.method.encode(data)


def child(source, root, cert, key, method, rate):
    source, root = Path(source), Path(root); root.mkdir()
    workers=4 if method.endswith('-w4') else 1
    if workers==4: method=method[:-3]
    start,cpu=time.perf_counter(),time.process_time()
    metrics={'http_plaintext_bytes':0}; lock=threading.Lock()
    packed=method.startswith('bundle-')
    prep={}
    if packed:
        codec=method.split('-')[1]
        size=65536 if method.endswith('-64k') else 1024*1024
        serving=root/'serving'; serving.mkdir()
        prep=pack(source,serving/'snapshot.utb',codec=codec,group_bytes=size)
    else: serving=source
    compression='none' if packed or method=='files-raw' else 'predictive' if method=='files-predictive' else 'ultra'
    token=secrets.token_urlsafe(48)
    with ExitStack() as stack:
        if method in ('files-zstd1','files-zstd3','files-lzma1'):
            ref={'files-zstd1':'zstd1-shuffle1','files-zstd3':'zstd3-shuffle1','files-lzma1':'lzma1'}[method]
            stack.enter_context(patch('ultra.network.AdaptiveEncoder',side_effect=lambda *a,**k:Encoder(ref)))
            stack.enter_context(patch('ultra.blockstream.unframe',Method(ref,rate).decode))
        server=make_server(LocalSource(serving),('127.0.0.1',0),cert,key,token,compression,link_mbps=rate)
        parent=server.RequestHandlerClass
        class Measured(parent):
            def setup(self):
                super().setup(); self.wfile=MeteredWriter(self.wfile,rate*1e6/8,metrics,lock)
        server.RequestHandlerClass=Measured
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        try:
            remote=RemoteSource(f'https://localhost:{server.server_port}',token,cert,compression)
            transport=Transfer(remote,root/'received',Options(workers=workers)).run()
            if transport.errors: raise RuntimeError(transport.errors)
            if packed:
                restore_start=time.perf_counter()
                result=Transfer(BundleSource(root/'received'/'snapshot.utb'),root/'restored',Options(workers=1)).run()
                restore_seconds=time.perf_counter()-restore_start
                destination=root/'restored'
                if result.errors: raise RuntimeError(result.errors)
            else: destination=root/'received'; restore_seconds=0
            seconds=time.perf_counter()-start; cpu_seconds=time.process_time()-cpu
            # Independent final inventory/digests: deliberately outside timer.
            expected=inventory(source); actual=inventory(destination,exclude_state=True)
            if [(e.path,e.kind,e.size) for e in expected] != [(e.path,e.kind,e.size) for e in actual]:
                raise RuntimeError('Inventory mismatch')
            for e in expected:
                if e.kind=='file' and digest(source/e.path)!=digest(destination/e.path): raise RuntimeError('Digest mismatch')
            rss=int(next(l.split()[1] for l in Path('/proc/self/status').read_text().splitlines() if l.startswith('VmHWM:')))
            return dict(seconds=seconds,cpu_seconds=cpu_seconds,max_rss_kib=rss,restore_seconds=restore_seconds,
                        **metrics,**prep,requests=server.transfer_metrics['file_requests'],verified=True)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)


def fixtures(base):
    result={};rng=random.Random(994821)
    for name in ('json_related','stdlib_real','gzip_noise'):
        root=base/name;root.mkdir();(root/'dossier vide').mkdir();(root/'.caché').write_bytes(b'')
        if name=='stdlib_real':
            paths=sorted(Path(sysconfig.get_paths()['stdlib']).glob('*.py'))
            for i,p in enumerate(paths[:160]):
                # Actual files, not truncated to force the small-file boundary.
                if p.stat().st_size<=65536: (root/p.name).write_bytes(p.read_bytes())
        else:
            for i in range(160):
                content=(json.dumps({'sequence':i,'machine':'edge-'+str(i%37),'status':'ok','message':'inventory synchronized'})+'\n').encode()*32
                if name=='gzip_noise': content=gzip.compress(rng.randbytes(3072),mtime=0)
                (root/f'été-{i:04}.bin').write_bytes(content)
        result[name]=root
    root=base/'mixed_heldout';root.mkdir();(root/'dossier vide').mkdir()
    rng=random.Random(381199)
    for i in range(240):
        if i%3==0: content=(f'<item id="{i}" status="ready">warehouse route</item>\n'.encode()*390)
        elif i%3==1: content=gzip.compress(rng.randbytes(19000),mtime=0)
        else: content=rng.randbytes(19000)
        (root/f'validation-{i:04}.bin').write_bytes(content)
    (root/'.caché').write_bytes(b'');result['mixed_heldout']=root
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--rounds',type=int,default=5)
    p.add_argument('--mbps',type=float,nargs='+',default=[50,1000])
    p.add_argument('--methods',nargs='+',default=['files-raw','files-raw-w4','files-zstd1-w4','files-predictive','files-zstd1','files-zstd3','files-lzma1','bundle-raw','bundle-auto','bundle-zstd1','bundle-zstd3','bundle-lzma1'])
    p.add_argument('--output',type=Path,default=Path('reports/bundle-r4.json'))
    p.add_argument('--only',nargs='+');p.add_argument('--child',nargs=7);a=p.parse_args()
    if a.child:
        src,root,cert,key,method,rate,unused=a.child
        print(json.dumps(child(src,root,cert,key,method,float(rate))));return
    if not 1<=a.rounds<=9 or any(r<=0 or r>10000 for r in a.mbps): p.error('Invalid bounds')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='ultra-bundle-r4-') as tmp:
        base=Path(tmp); inputs=fixtures(base);cert=base/'cert.pem';key=base/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if a.only: inputs={name:inputs[name] for name in a.only}
        checksums={name:{e.path:digest(root/e.path) for e in inventory(root) if e.kind=='file'} for name,root in inputs.items()}
        jobs=[(name,m,rate,i) for name in inputs for m in a.methods for rate in a.mbps for i in range(a.rounds)]
        random.Random(44219).shuffle(jobs)
        for j,(name,method,rate,i) in enumerate(jobs):
            dest=base/f'job-{j}'
            out=subprocess.check_output([sys.executable,'-m','research.benchmark_bundle_r4','--child',str(inputs[name]),str(dest),str(cert),str(key),method,str(rate),'unused'],text=True)
            row=dict(dataset=name,method=method,mbps=rate,round=i,**json.loads(out));rows.append(row)
            a.output.with_suffix('.partial.json').write_text(json.dumps(rows,indent=2))
            shutil.rmtree(dest)
            if j%10==0: print(f'{j+1}/{len(jobs)} verified',flush=True)
        summary=[]
        for name in inputs:
            for method in a.methods:
                for rate in a.mbps:
                    selected=[r for r in rows if (r['dataset'],r['method'],r['mbps'])==(name,method,rate)]
                    summary.append(dict(dataset=name,method=method,mbps=rate,
                        **{'median_'+k:statistics.median(r[k] for r in selected) for k in ('seconds','cpu_seconds','max_rss_kib','http_plaintext_bytes','requests','restore_seconds')},
                        min_seconds=min(r['seconds'] for r in selected),max_seconds=max(r['seconds'] for r in selected)))
        a.output.write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),rounds=a.rounds,
            scope='Actual Linux authenticated TLS loopback, warm caches, one worker except explicit -w4 direct references, paced application output per connection (four workers can reach four times the nominal aggregate rate, favoring those references). Includes bundle preparation + container fsync, server inventory/hash/TLS setup, transfer and engine checks, bounded decode + file hash validation, ordinary engine rehydration/write/fsync/final verification. Independent extra inventory/digests, fixture/certificate creation, imports and server shutdown excluded. RSS high water isolated process includes imports/codecs/both endpoints/independent verification; CPU timer covers both endpoints. No RTT/loss emulation, distinct hosts, physical USB, Windows, RDP, or representative enterprise corpus. Fixed codecs are known per method, no novel compression claim. No bundling production negotiation/resume at logical-file granularity.',
            dataset_sha256=checksums,summary=summary,raw=rows),indent=2))
        a.output.with_suffix('.partial.json').unlink(missing_ok=True)

if __name__=='__main__': main()
