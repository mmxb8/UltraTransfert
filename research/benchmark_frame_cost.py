"""Before/after frame costs and explicitly negotiated predictive HTTPS.

The two legacy functions below preserve the operations at f95b002. They are
benchmark references only. Run from the repository root with -m research.
"""
import argparse
from contextlib import ExitStack
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import secrets
import statistics
import struct
import subprocess
import sysconfig
import tempfile
import threading
import time
import tracemalloc
from unittest.mock import patch

from ultra import compression, predictive
from ultra.compression import CodecError, MAX_BLOCK
from ultra.engine import LocalSource, Options, Transfer, digest
from ultra.network import RemoteSource, make_server
from research.benchmark_https_compression import MeteredWriter


class LegacyZstd(compression.Zstd):
    """Exact buffer extraction used by the reference commit."""
    def compress(self, data, level):
        out=C.create_string_buffer(self.lib.ZSTD_compressBound(len(data)))
        n=self.checked(self.lib.ZSTD_compress(out,len(out),data,len(data),level))
        return out.raw[:n]

    def decompress(self, data, size):
        if self.checked(self.lib.ZSTD_findFrameCompressedSize(data,len(data)))!=len(data):
            raise CodecError('Données après la trame Zstandard')
        out=C.create_string_buffer(max(1,size))
        n=self.checked(self.lib.ZSTD_decompress(out,size,data,len(data)))
        if n!=size:
            raise CodecError('Longueur Zstandard incorrecte')
        return out.raw[:n]


def legacy_frame(data, recipe=('raw',1,'none'), *, fallback=True):
    if len(data)>MAX_BLOCK:
        raise CodecError('Predictor block too large')
    codec,width,predictor=recipe
    if codec not in ('raw','zlib1','zstd1','zstd3'):
        raise CodecError('Invalid codec')
    transformed=compression.shuffle(predictive.predict(data,width,predictor),width)
    result=predictive._prefix(data,recipe)+compression.compress(transformed,codec)
    if fallback and recipe!=('raw',1,'none'):
        raw_prefix=predictive._prefix(data,('raw',1,'none'))
        if len(result)>len(raw_prefix)+len(data):
            return raw_prefix+data
    return result


def revision_context(revision, old_zstd):
    stack=ExitStack()
    if revision=='before':
        stack.enter_context(patch('ultra.compression.ZSTD',old_zstd))
        stack.enter_context(patch('ultra.predictive.frame',legacy_frame))
        stack.enter_context(patch('ultra.predictive_budget.frame',legacy_frame))
    return stack


def inputs(size=MAX_BLOCK):
    rng=random.Random(2601116)
    stdlib=Path(sysconfig.get_paths()['stdlib'])
    source=bytearray()
    for path in sorted(stdlib.glob('*.py')):
        source.extend(path.read_bytes())
        if len(source)>=size:
            break
    return {'random':rng.randbytes(size),
            'repeated':(b'UltraTransfert verified bytes\n'*(size//29+1))[:size],
            'float32':b''.join(struct.pack('<f',math.sin(i*.00091)+.00007*(i%17))
                               for i in range(size//4)),
            'stdlib':bytes(source[:size])}


def micro(data, rounds, old_zstd):
    recipes=[('raw',1,'none'),('zlib1',4,'none')]
    if old_zstd:
        recipes.extend([('zstd1',1,'none'),('zstd3',4,'subtract')])
    jobs=[(name,recipe,revision,iteration) for name in data for recipe in recipes
          for revision in ('before','after') for iteration in range(rounds)]
    random.Random(91266).shuffle(jobs)
    rows=[]
    for name,recipe,revision,iteration in jobs:
        with revision_context(revision,old_zstd):
            start=time.perf_counter();cpu=time.process_time()
            encoded=predictive.frame(data[name],recipe)
            restored=predictive.unframe(encoded)
            elapsed=time.perf_counter()-start;cpu=time.process_time()-cpu
        if restored!=data[name]:
            raise RuntimeError('Roundtrip mismatch')
        rows.append(dict(dataset=name,recipe=list(recipe),revision=revision,
                         round=iteration,seconds=elapsed,cpu_seconds=cpu,
                         frame_bytes=len(encoded)))
    memory=[]
    for name in data:
        for recipe in recipes:
            for revision in ('before','after'):
                peaks=[]
                for _ in range(3):
                    with revision_context(revision,old_zstd):
                        tracemalloc.start()
                        encoded=predictive.frame(data[name],recipe)
                        _,peak=tracemalloc.get_traced_memory()
                        tracemalloc.stop()
                        restored=predictive.unframe(encoded)
                    if restored!=data[name]:
                        raise RuntimeError('Memory roundtrip mismatch')
                    peaks.append(peak)
                memory.append(dict(dataset=name,recipe=list(recipe),revision=revision,
                                   python_encode_peak_bytes=statistics.median(peaks)))
    return rows,memory


def https(data, rounds, old_zstd):
    methods=('before-adaptive','after-adaptive','before-fixed-zlib',
             'after-fixed-zlib','none','gzip')
    jobs=[(name,rate,method,iteration) for name in data for rate in (50,1000)
          for method in methods for iteration in range(rounds)]
    random.Random(213517).shuffle(jobs)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='ultra-frame-cost-') as temp:
        base=Path(temp);cert,key=base/'cert.pem',base/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes',
                        '-keyout',str(key),'-out',str(cert),'-days','1','-subj',
                        '/CN=localhost','-addext','subjectAltName=DNS:localhost'],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for number,(name,rate,method,iteration) in enumerate(jobs):
            root=base/str(number);source=root/'source';source.mkdir(parents=True)
            (source/'été.bin').write_bytes(data[name]);(source/'vide').touch()
            (source/'dossier vide').mkdir()
            mode=method if method in ('none','gzip') else 'predictive'
            revision=method.split('-')[0]
            with revision_context(revision,old_zstd) as stack:
                if method.endswith('fixed-zlib'):
                    class Fixed:
                        searches=reused=0
                        def encode(self, block):
                            return predictive.frame(block,('zlib1',4,'none'))
                    stack.enter_context(patch('ultra.network.BudgetEncoder',
                                              side_effect=lambda *a,**k:Fixed()))
                token=secrets.token_urlsafe(32)
                start=time.perf_counter();cpu=time.process_time()
                server=make_server(LocalSource(source),('127.0.0.1',0),cert,key,
                                   token,mode,link_mbps=rate)
                metrics={'http_plaintext_bytes':0};lock=threading.Lock()
                parent=server.RequestHandlerClass
                class Metered(parent):
                    def setup(self):
                        super().setup()
                        self.wfile=MeteredWriter(self.wfile,rate*1e6/8,metrics,lock)
                server.RequestHandlerClass=Metered
                thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True)
                thread.start()
                try:
                    remote=RemoteSource(f'https://localhost:{server.server_port}',token,cert,mode)
                    result=Transfer(remote,root/'destination',Options(workers=1)).run()
                    elapsed=time.perf_counter()-start;cpu=time.process_time()-cpu
                    if result.errors or digest(root/'destination'/'été.bin')!=hashlib.sha256(data[name]).hexdigest():
                        raise RuntimeError(result.errors or 'Independent hash mismatch')
                    if (root/'destination'/'vide').read_bytes()!=b'' or not (root/'destination'/'dossier vide').is_dir():
                        raise RuntimeError('Empty entry missing')
                    rows.append(dict(dataset=name,mbps=rate,method=method,round=iteration,
                                     seconds=elapsed,cpu_seconds=cpu,**metrics,
                                     server_metrics=dict(server.transfer_metrics)))
                finally:
                    server.shutdown();server.server_close();thread.join(timeout=5)
            if (number+1)%20==0:
                print(f'HTTPS {number+1}/{len(jobs)} verified',flush=True)
    return rows


def summaries(rows, keys, values):
    groups={}
    for row in rows:
        key=tuple(json.dumps(row[k],sort_keys=True) for k in keys)
        groups.setdefault(key,[]).append(row)
    return [{**{k:group[0][k] for k in keys},'samples':len(group),
             **{f'median_{v}':statistics.median(r[v] for r in group) for v in values},
             'min_seconds':min(r['seconds'] for r in group),
             'max_seconds':max(r['seconds'] for r in group)} for group in groups.values()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds',type=int,default=9)
    parser.add_argument('--https-rounds',type=int,default=5)
    parser.add_argument('--output',type=Path,default=Path('reports/frame-cost.json'))
    args=parser.parse_args()
    if not 1<=args.rounds<=20 or not 0<=args.https_rounds<=10:
        parser.error('rounds 1–20, HTTPS rounds 0–10')
    data=inputs();old_zstd=LegacyZstd() if compression.ZSTD else None
    raw,memory=micro(data,args.rounds,old_zstd)
    print('Microbenchmarks completed',flush=True)
    tls=https({k:v[:2*1024*1024] for k,v in data.items() if k!='repeated'},
              args.https_rounds,old_zstd) if args.https_rounds else []
    result=dict(python=platform.python_version(),platform=platform.platform(),
                zstd_version=old_zstd.version if old_zstd else None,
                reference_commit='f95b0023fc2fd0bd187e09c0a4dac3e6a01cdd53',
                dataset_sha256={k:hashlib.sha256(v).hexdigest() for k,v in data.items()},
                dataset_bytes={k:len(v) for k,v in data.items()},
                scope='Linux warm caches. Micro time includes encode+decode; memory is encode-only Python traced peak, excluding native codec workspaces and input. TLS is authenticated loopback, one worker, 2-MiB prefixes, capped per connection at 50/1000 Mbps in 16-KiB writes; includes inventory/hash/server setup/client TLS/codec/destination fsync/final engine checks, excludes fixtures, certificate generation, shutdown and extra independent hash. No physical network, Windows, RDP, representative corpus or market-wide superiority. Before/after adaptive choices depend on timing; fixed zlib comparison isolates frame changes and matches the codec available in the bundled Windows runtime. none/gzip are existing transport references. Before uses frozen frame/buffer routines at reference commit; all SHA256 and stream checks retained. Jobs randomized; raw samples and regressions retained.',
                micro_summary=summaries(raw,('dataset','recipe','revision'),('seconds','cpu_seconds','frame_bytes')),
                micro_raw=raw,memory=memory,
                https_summary=summaries(tls,('dataset','mbps','method'),('seconds','cpu_seconds','http_plaintext_bytes')),
                https_raw=tls)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(f'Saved {args.output}: {len(raw)} CPU roundtrips, {len(tls)} TLS copies',flush=True)


if __name__=='__main__':
    main()
