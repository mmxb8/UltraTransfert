"""Isolated reader benchmark: frames prepared before timing, not a transfer gain."""
import argparse
import hashlib
import io
import json
import random
import statistics
import time
import tracemalloc
from unittest.mock import patch

from ultra.blockstream import BlockReader, write_stream
from ultra.compression import frame
from research.predictive_compression import frame as predictive_frame, unframe
from research.stream_reader_r3 import LeanBlockReader, raw_view_unframe


class Encoder:
    searches=reused=0
    def __init__(self,kind):self.kind=kind
    def encode(self,data):
        return frame(data) if self.kind=='UTCL1' else predictive_frame(data)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rounds',type=int,default=15)
    p.add_argument('--output',default='reports/reader-r3-memory.json')
    a=p.parse_args()
    data=random.Random(351205).randbytes(16*1024*1024+117)
    encoded={}
    for kind in ('UTCL1','UTCP1'):
        out=io.BytesIO();write_stream(io.BytesIO(data),out,len(data),Encoder(kind));encoded[kind]=out.getvalue()
    jobs=[(kind,size,cls,i) for kind in encoded for size in (65536,1048576,4194304)
          for cls in (BlockReader,LeanBlockReader) for i in range(a.rounds)]
    random.Random(19281).shuffle(jobs)
    rows=[]
    def run(kind,size,cls):
        r=cls(io.BytesIO(encoded[kind]),len(data));sha=hashlib.sha256()
        with patch('ultra.blockstream.unframe',raw_view_unframe if cls is LeanBlockReader else unframe) if kind=='UTCP1' else patch('ultra.blockstream.unframe',__import__('ultra.compression',fromlist=['unframe']).unframe):
            while chunk:=r.read(size):sha.update(chunk)
        if sha.hexdigest()!=hashlib.sha256(data).hexdigest():raise RuntimeError('digest mismatch')
    for kind,size,cls,i in jobs:
        cpu=time.process_time();t=time.perf_counter();run(kind,size,cls)
        rows.append({'format':kind,'buffer_bytes':size,'reader':cls.__name__,'round':i,
                     'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu})
    summary=[]
    for kind in encoded:
        for size in (65536,1048576,4194304):
            for cls in (BlockReader,LeanBlockReader):
                rr=[r for r in rows if r['format']==kind and r['buffer_bytes']==size and r['reader']==cls.__name__]
                tracemalloc.start();run(kind,size,cls);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                summary.append({'format':kind,'buffer_bytes':size,'reader':cls.__name__,
                                'median_wall_seconds':statistics.median(r['wall_seconds'] for r in rr),
                                'median_cpu_seconds':statistics.median(r['cpu_seconds'] for r in rr),
                                'python_peak_bytes':peak})
    from pathlib import Path
    Path(a.output).write_text(json.dumps({'input_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
          'scope':'Isolated decoding of prebuilt in-memory raw frames, includes block/stream SHA256 plus consumer SHA256 and independent final digest computation. Excludes encoding, network and filesystem. Python traced allocations exclude native buffers and prebuilt inputs. Not end-to-end transfer.',
          'rounds':a.rounds,'summary':summary,'raw':rows},indent=2)+'\n')
    for kind in encoded:
        rr=[r for r in summary if r['format']==kind and r['buffer_bytes']==1048576]
        print(kind,rr)


if __name__=='__main__':main()
