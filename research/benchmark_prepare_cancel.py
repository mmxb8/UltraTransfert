"""Lectures/hachage réels, annulation déclenchée à 8 Mio ; boucle locale Linux."""
import builtins
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch

from ultra import network
from ultra.engine import LocalSource, OperationCancelled, digest


def main():
    spec=importlib.util.spec_from_file_location('ultra.previous_network',Path('history/v0.3.9/ultra/network.py'))
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);src=root/'source';src.mkdir();file=src/'64M.bin'
        with file.open('wb') as f:
            for _ in range(64):f.write(bytes(range(256))*4096)
        expected=digest(file)
        cert,key=root/'cert.pem',root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for iteration in range(6):
            for name in (('previous','current') if iteration%2==0 else ('current','previous')):
                cancel=threading.Event();count=[0];requested=[None];server=None;cancelled=False
                class Reader:
                    def __init__(self,stream):self.stream=stream
                    def __enter__(self):return self
                    def __exit__(self,*a):self.stream.close()
                    def read(self,n):
                        data=self.stream.read(n);count[0]+=len(data)
                        if count[0]>=8*1024*1024 and requested[0] is None:
                            requested[0]=time.perf_counter();cancel.set()
                        return data
                def opening(path,*a,**kw):
                    stream=builtins.open(path,*a,**kw)
                    return Reader(stream) if Path(path)==file else stream
                module=previous if name=='previous' else network
                start=time.perf_counter()
                try:
                    with patch('ultra.engine.open',side_effect=opening,create=True):
                        server=module.make_server(LocalSource(src),('127.0.0.1',0),cert,key,'benchmark-'+'x'*48,**({'cancel':cancel} if name=='current' else {}))
                except OperationCancelled:cancelled=True
                elapsed=time.perf_counter()-start
                after=time.perf_counter()-requested[0]
                if server:server.server_close()
                assert cancelled==(name=='current')
                assert count[0]==(8 if cancelled else 64)*1024*1024
                rows.append({'method':name,'round':iteration,'read_bytes':count[0],'seconds':elapsed,'seconds_after_request':after,'cancelled':cancelled,'listener_constructed':server is not None})
        assert digest(file)==expected
    summary={n:{'median_seconds':statistics.median(r['seconds'] for r in rows if r['method']==n),'median_after_request_seconds':statistics.median(r['seconds_after_request'] for r in rows if r['method']==n)} for n in ('previous','current')}
    report={'measurement':'Six alternating repetitions, real 64-MiB synthetic source reads/SHA-256 with warm caches on Linux. Simulated cancellation request at exactly 8 MiB read; old make_server cannot accept cancellation and finishes hashing/binds loopback, immediately closed without serving. New make_server cancels. Includes LocalSource inventory, hashing and applicable server setup. Fixture certificate creation excluded; no file transfer, Windows, GUI rendering, RDP or blocked-device latency simulation. Saved work is not higher throughput.','summary':summary,'raw':rows,'source_sha256':expected}
    Path('reports/prepare-cancel-0.3.10.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
