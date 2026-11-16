"""Held-out synthetic and actual local file bytes; no network in this benchmark.

All methods include framing and SHA-256. Serial transfer times are ESTIMATES.
No compressor is given a precomputed dictionary or free pre-processing.
"""
import argparse
import ctypes as C
import ctypes.util
import gzip
import hashlib
import json
import lzma
import math
from pathlib import Path
import platform
import random
import sqlite3
import statistics
import struct
import sysconfig
import tempfile
import time
import tracemalloc

from ultra.compression import MAX_BLOCK, ZSTD, AdaptiveEncoder, frame as old_frame, unframe as old_unframe
from research.predictive_compression import PredictiveEncoder, frame, unframe, predict


class Blosc:
    """Trusted local benchmark inputs only; one compression/decompression thread."""
    def __init__(self):
        path = ctypes.util.find_library('blosc')
        if not path:
            raise OSError('No system Blosc')
        self.lib = C.CDLL(path)
        self.lib.blosc_compress_ctx.argtypes = [C.c_int,C.c_int,C.c_size_t,C.c_size_t,C.c_void_p,C.c_void_p,C.c_size_t,C.c_char_p,C.c_size_t,C.c_int]
        self.lib.blosc_compress_ctx.restype = C.c_int
        self.lib.blosc_decompress_ctx.argtypes = [C.c_void_p,C.c_void_p,C.c_size_t,C.c_int]
        self.lib.blosc_decompress_ctx.restype = C.c_int
        self.lib.blosc_get_version_string.restype = C.c_char_p
        self.version = self.lib.blosc_get_version_string().decode()

    def compress(self, data, codec, width, bitshuffle=False):
        out = C.create_string_buffer(len(data)+16)
        n = self.lib.blosc_compress_ctx(3,2 if bitshuffle else 1,width,len(data),data,out,len(out),codec.encode(),0,1)
        if n <= 0:
            raise RuntimeError('Blosc compression failed')
        return out.raw[:n]

    def decompress(self, data, size):
        out = C.create_string_buffer(max(1,size))
        n = self.lib.blosc_decompress_ctx(data,out,size,1)
        if n != size:
            raise RuntimeError('Blosc decompression failed')
        return out.raw[:n]


try:
    BLOSC = Blosc()
except (OSError, AttributeError):
    BLOSC = None


def datasets(size=2*1024*1024):
    # Frequencies and noise seed differ from the exploratory 0.001 sine signal.
    rng = random.Random(170119)
    noise = rng.randbytes(size)
    signal = b''.join(struct.pack('<f',math.sin(i*.00073)+.00005*(i%11)) for i in range(size//4))
    counters = b''.join(struct.pack('<Q',1700000000000000+i*1000+(i%13)) for i in range(size//8))
    stdlib = Path(sysconfig.get_paths()['stdlib'])
    sources = bytearray()
    for p in sorted(stdlib.glob('*.py')):
        sources.extend(p.name.encode()+b'\0'+p.read_bytes()+b'\0')
        if len(sources) >= size:
            break
    executable = Path('/usr/bin/python3').read_bytes()[:size]
    rows = b''.join(json.dumps({'sequence':i,'machine':'edge-'+str(i%37),'bytes':rng.randrange(100000),
                                'status':'ok' if i%71 else 'retry'}).encode()+b'\n' for i in range(size//90))
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp)/'sample.db'
        conn = sqlite3.connect(db)
        conn.execute('CREATE TABLE events (id INTEGER PRIMARY KEY, machine TEXT, amount INTEGER, note TEXT)')
        conn.executemany('INSERT INTO events VALUES (?,?,?,?)',
                         ((i,'edge-'+str(i%37),rng.randrange(100000),'completed' if i%71 else 'retry') for i in range(size//64)))
        conn.commit();conn.close()
        sqlite = db.read_bytes()[:MAX_BLOCK]
    return {'float32_held_out_synthetic':signal,
            'uint64_timestamps_synthetic':counters,
            'json_events_synthetic':rows,
            'sqlite_events_synthetic':sqlite,
            'actual_python_stdlib_bytes':bytes(sources[:size]),
            'actual_python_elf_prefix':executable,
            'gzip_pseudorandom':gzip.compress(noise,compresslevel=1,mtime=0),
            'mixed_json_pseudorandom':rows[:len(rows)//2]+noise[:size//2]}


class Method:
    def __init__(self,name,rate):
        self.name,self.rate = name,rate
        self.encoder = None
        if name == 'predictive_initial':
            from research.predictive_compression_initial import PredictiveEncoder as InitialEncoder
            self.encoder = InitialEncoder(rate)
        elif name == 'budget_R21':
            from research.budget_compression_r21 import BudgetEncoder
            self.encoder = BudgetEncoder(rate)
        elif name in ('budget_R2','budget_R3'):
            from research.budget_compression import BudgetEncoder
            self.encoder = BudgetEncoder(rate)
        elif name == 'predictive':
            self.encoder = PredictiveEncoder(rate)
        elif name == 'ultra_0.4.0':
            self.encoder = AdaptiveEncoder(rate)

    def encode(self,data):
        if self.encoder:
            return self.encoder.encode(data)
        if self.name.startswith('utcp-raw'):
            return frame(data)
        if self.name.startswith('utcp-subtract4'):
            return frame(data,('zstd3',4,'subtract'))
        if self.name == 'raw' or self.name.startswith('raw_blocks_'):
            return old_frame(data)
        if self.name.startswith('zstd'):
            level,width = self.name.split('-shuffle')
            return old_frame(data,level,int(width))
        if self.name.startswith('fixed-subtract'):
            return frame(data,('zstd3',4,'subtract'))
        if self.name.startswith('lzma'):
            preset = int(self.name[4])
            if self.name.endswith('-delta4'):
                filters = [{'id':lzma.FILTER_DELTA,'dist':4},{'id':lzma.FILTER_LZMA2,'preset':preset}]
                payload = lzma.compress(data,filters=filters)
            else:
                payload = lzma.compress(data,preset=preset)
        elif self.name.startswith('blosc'):
            _,codec,kind,width = self.name.split('-')
            payload = BLOSC.compress(data,codec,int(width),kind=='bitshuffle')
        else:
            raise ValueError(self.name)
        # Equal digest/size envelope for external codecs; included in byte count.
        return struct.pack('!Q',len(data))+hashlib.sha256(data).digest()+payload

    def decode(self,encoded):
        if self.name.startswith('utcp-') or self.name in ('predictive','budget_R2','budget_R3','budget_R21','predictive_initial','fixed-subtract4-zstd3'):
            return unframe(encoded)
        if self.name == 'ultra_0.4.0' or self.name == 'raw' or self.name.startswith(('zstd','raw_blocks_')):
            return old_unframe(encoded)
        size = struct.unpack('!Q',encoded[:8])[0]
        if self.name.startswith('lzma'):
            data = lzma.decompress(encoded[40:])
        else:
            data = BLOSC.decompress(encoded[40:],size)
        if len(data)!=size or hashlib.sha256(data).digest()!=encoded[8:40]:
            raise RuntimeError('External codec roundtrip mismatch')
        return data


def method_names():
    names = ['raw','ultra_0.4.0','predictive_initial','predictive','lzma1','lzma6','lzma6-delta4']
    if ZSTD:
        names += ['zstd1-shuffle1','zstd3-shuffle1','zstd3-shuffle4','zstd3-shuffle8','fixed-subtract4-zstd3']
    if BLOSC:
        names += ['blosc-zstd-shuffle-4','blosc-zstd-bitshuffle-4','blosc-zstd-bitshuffle-8','blosc-lz4-bitshuffle-4']
    return names


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rounds',type=int,default=5)
    p.add_argument('--methods',nargs='+',default=None)
    p.add_argument('--mbps',type=float,nargs='+',default=[10,50,1000])
    p.add_argument('--output',type=Path,default=Path('reports/predictive-cpu.json'))
    a = p.parse_args()
    if not 1 <= a.rounds <= 20 or any(not math.isfinite(x) or x<=0 for x in a.mbps):
        p.error('Invalid rounds or bandwidth')
    inputs = datasets()
    names = a.methods or method_names()
    jobs = [(n,m,r,i) for n in inputs for m in names for r in a.mbps for i in range(a.rounds)]
    random.Random(71942).shuffle(jobs)
    raw = []
    for j,(name,method,rate,i) in enumerate(jobs):
        data = inputs[name]
        cpu_start = time.process_time();start = time.perf_counter()
        m = Method(method,rate)
        encoded = m.encode(data)
        enc = time.perf_counter()-start
        start = time.perf_counter();decoded = m.decode(encoded);dec = time.perf_counter()-start
        cpu = time.process_time()-cpu_start
        if decoded != data:
            raise RuntimeError((name,method,'incorrect bytes'))
        raw.append({'dataset':name,'method':method,'link_mbps':rate,'round':i,
                    'input_bytes':len(data),'encoded_bytes':len(encoded),
                    'encode_seconds':enc,'decode_seconds':dec,'cpu_seconds':cpu,
                    'estimated_serial_seconds':enc+dec+len(encoded)/(rate*1e6/8),
                    'recipe':m.encoder.recipe if m.encoder else None})
        if j%50 == 0:
            print(f'{j+1}/{len(jobs)} completed',flush=True)
    summary = []
    for n in inputs:
        for rate in a.mbps:
            for method in names:
                rows = [r for r in raw if r['dataset']==n and r['method']==method and r['link_mbps']==rate]
                row = {'dataset':n,'method':method,'link_mbps':rate,'input_bytes':len(inputs[n])}
                for key in ('encoded_bytes','encode_seconds','decode_seconds','cpu_seconds','estimated_serial_seconds'):
                    row['median_'+key] = statistics.median(r[key] for r in rows)
                row['min_estimated_serial_seconds'] = min(r['estimated_serial_seconds'] for r in rows)
                row['max_estimated_serial_seconds'] = max(r['estimated_serial_seconds'] for r in rows)
                summary.append(row)
    # Untimed instrumented allocations, separate from timings above. Native library
    # workspaces are not visible to tracemalloc; this is NOT total process RSS.
    memory = []
    for name in inputs:
        for method in ('raw','ultra_0.4.0','predictive','budget_R2'):
            tracemalloc.start()
            m = Method(method,50);encoded=m.encode(inputs[name]);decoded=m.decode(encoded)
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            assert decoded == inputs[name]
            memory.append({'dataset':name,'method':method,'python_traced_peak_bytes':peak})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({'python':platform.python_version(),'platform':platform.platform(),
        'zstd_version':ZSTD.version if ZSTD else None,'blosc_version':BLOSC.version if BLOSC else None,
        'rounds':a.rounds,'methods':names,'dataset_sha256':{n:hashlib.sha256(d).hexdigest() for n,d in inputs.items()},
        'scope':'Measured encode+decode+SHA256/framing CPU and wall times. Estimated serial total adds frame_bytes/bandwidth. No actual network, disk, RTT/loss, RDP, pipeline overlap or Windows. Warm caches, one Blosc thread; 2-MiB-scale inputs, new encoder per measurement. LZMA uses stdlib XZ container, not 7-Zip executable. Blosc1 is not Blosc2 or TurboPFor. Native workspaces excluded from Python-traced memory. External baseline envelopes have 40 bytes; UTCL1/UTCP1 headers differ and all bytes are counted. Actual stdlib and ELF inputs plus six synthetic datasets; no claim of representative enterprise population or novelty.',
        'summary':summary,'raw':raw,'memory':memory},indent=2),encoding='utf8')
    for n in inputs:
        group=[r for r in summary if r['dataset']==n and r['link_mbps']==50]
        if group:
            best=min((r for r in group if r['method'] not in ('predictive','budget_R2','budget_R3','budget_R21','predictive_initial','fixed-subtract4-zstd3')),key=lambda r:r['median_estimated_serial_seconds'])
            pred=next(r for r in group if r['method']=='predictive')
            print(json.dumps({'dataset':n,'best_reference':best['method'],'baseline_seconds':best['median_estimated_serial_seconds'],
                              'predictive_seconds':pred['median_estimated_serial_seconds'],
                              'gain_percent':100*(1-pred['median_estimated_serial_seconds']/best['median_estimated_serial_seconds'])}))


if __name__ == '__main__':
    main()
