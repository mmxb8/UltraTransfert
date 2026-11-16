"""Plafond logique, 1/4 workers, local et TLS loopback ; aucun RDP réel."""
import json
from pathlib import Path
import random
import secrets
import statistics
import subprocess
import tempfile
import threading
import time

from ultra.engine import LocalSource,Options,Transfer,digest
from ultra.network import RemoteSource,make_server


def main():
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);src=root/'source';src.mkdir();rng=random.Random(891)
        for i in range(4):(src/f'été_{i}.bin').write_bytes(rng.randbytes(2*1024*1024))
        (src/'vide').touch();(src/'dossier vide').mkdir()
        expected={p.name:digest(p) for p in src.iterdir() if p.is_file()}
        cert,key=root/'cert.pem',root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        token=secrets.token_urlsafe(48);begin=time.perf_counter()
        server=make_server(LocalSource(src),('127.0.0.1',0),cert,key,token,'none')
        preparation=time.perf_counter()-begin
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        try:
            jobs=[(transport,workers,rate,i) for transport in ('local','https') for workers in (1,4) for rate in (0,4e6,16e6) for i in range(3)]
            random.Random(78).shuffle(jobs)
            for number,(transport,workers,rate,iteration) in enumerate(jobs):
                destination=root/f'dest-{number}';started=time.perf_counter()
                source=LocalSource(src) if transport=='local' else RemoteSource(f'https://localhost:{server.server_port}',token,cert,'none')
                result=Transfer(source,destination,Options(workers=workers,buffer_size=65536,max_bytes_per_second=rate)).run()
                elapsed=time.perf_counter()-started
                if result.errors:raise RuntimeError(result.errors)
                assert {n:digest(destination/n) for n in expected}==expected
                assert (destination/'dossier vide').is_dir()
                if rate:assert elapsed>=result.bytes/rate*.99
                rows.append({'transport':transport,'workers':workers,'bytes_per_second':rate,'round':iteration,'seconds':elapsed,'bytes':result.bytes,'logical_MBps':result.bytes/elapsed/1e6,'independent_sha256':expected})
                import shutil
                shutil.rmtree(destination)
        finally:server.shutdown();server.server_close();thread.join(timeout=5)
    summary=[]
    for transport in ('local','https'):
        for workers in (1,4):
            for rate in (0,4e6,16e6):
                sample=[r for r in rows if (r['transport'],r['workers'],r['bytes_per_second'])==(transport,workers,rate)]
                summary.append({'transport':transport,'workers':workers,'bytes_per_second':rate,'median_seconds':statistics.median(r['seconds'] for r in sample),'min_seconds':min(r['seconds'] for r in sample),'max_seconds':max(r['seconds'] for r in sample),'median_logical_MBps':statistics.median(r['logical_MBps'] for r in sample)})
    report={'measurement':'36 actual copies, randomized order, three repetitions each, 8 MiB total in four synthetic files plus empty file/directory, warm caches Linux. Local or TLS loopback without compression. Includes per-copy inventory/client TLS manifest, copy, pacing, write/fsync and engine final verification. Shared HTTPS source/server setup measured separately, fixture certificate creation and extra independent SHA excluded. No latency/loss, physical media, Windows or RDP responsiveness measured. Limit concerns logical source bytes processed by copy, not physical wire traffic or verification I/O. No throughput gain claimed.','shared_server_preparation_seconds':preparation,'summary':summary,'raw':rows}
    Path('reports/pacing-0.3.11.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
