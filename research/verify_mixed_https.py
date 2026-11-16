"""Intégrité HTTPS ultra : 64 Mio, petits fichiers, Unicode et reprise locale TLS."""
import hashlib
import argparse
import json
from pathlib import Path
import random
import secrets
import subprocess
import tempfile
import threading
import time

from ultra.engine import LocalSource, Options, Transfer, digest
from ultra.network import RemoteSource, make_server


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('reports/mixed-https.json'))
    parser.add_argument('--selection-pruning',action='store_true')
    parser.add_argument('--compression', choices=['none','auto','gzip','ultra'], default='ultra')
    parser.add_argument('--large-mib', type=int, default=64)
    args=parser.parse_args()
    if not 16 <= args.large_mib <= 1024 or args.large_mib % 4:
        parser.error('16–1024 Mio, multiple de 4')
    with tempfile.TemporaryDirectory(prefix='ultra-mixed-https-') as tmp:
        root=Path(tmp);source=root/'source';source.mkdir()
        (source/'dossier vide 日本語').mkdir()
        (source/'vide').touch()
        (source/'.caché').write_bytes('caché'.encode('utf-8'))
        rng=random.Random(881)
        expected={}
        for i in range(256):
            path=source/f'petits été/العربية_日本語_{i}.bin';path.parent.mkdir(exist_ok=True)
            data=rng.randbytes(4096+i) if i%2 else b'donnees-exactes\n'*(i+1)
            path.write_bytes(data);expected[path.relative_to(source).as_posix()]=hashlib.sha256(data).hexdigest()
        sha=hashlib.sha256()
        with (source/'00-gros.bin').open('wb') as output:
            for _ in range(args.large_mib//4):
                block=rng.randbytes(4*1024*1024);output.write(block);sha.update(block)
        expected['00-gros.bin']=sha.hexdigest()
        expected['.caché']=digest(source/'.caché');expected['vide']=digest(source/'vide')
        cert,key=root/'cert.pem',root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        token=secrets.token_urlsafe(48)
        server=make_server(LocalSource(source),('127.0.0.1',0),cert,key,token,args.compression,link_mbps=1000,selection_pruning=args.selection_pruning)
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        try:
            remote=RemoteSource(f'https://localhost:{server.server_port}',token,cert,args.compression)
            destination=root/'destination';cancel=threading.Event()
            started=time.perf_counter()
            first=Transfer(remote,destination,Options(workers=1),lambda n,t:cancel.set() if n>=8*1024*1024 else None,cancel).run()
            assert first.errors and not (destination/'00-gros.bin').exists(),first
            result=Transfer(remote,destination,Options(workers=4)).run()
            assert not result.errors,result.errors
            assert result.resumed_bytes>0,result.resumed_bytes
            assert (destination/'dossier vide 日本語').is_dir()
            actual={p.relative_to(destination).as_posix():digest(p) for p in destination.rglob('*') if p.is_file() and '.ultratransfert-state' not in p.parts}
            assert actual==expected,'Inventaire/empreintes différents'
            assert {name:digest(source/name) for name in expected}==expected,'Source modifiée'
            report={'status':'passed','selection_pruning':args.selection_pruning,'files':len(actual),'compression':args.compression,'large_file_bytes':args.large_mib*1024*1024,
                    'resumed_bytes':result.resumed_bytes,'seconds':time.perf_counter()-started,
                    'server_metrics':dict(server.transfer_metrics),'independent_sha256':actual,
                    'measurement':'Actual TLS HTTPS selected compression loopback Linux, warm caches, no network cap. User cancellation after 8 MiB, partial unpublished, content-validated resume with four workers, Configurable large file plus 256 small mixed files, hidden/Unicode/empty files/directories; independent inventory/SHA-256 and source preservation. Integrity run, no before/after performance claim, no Windows/RDP or physical media.'}
            args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in report.items() if k!='independent_sha256'},indent=2))
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':main()
