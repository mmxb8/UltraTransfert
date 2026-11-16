"""Préparation automatique vs recette OpenSSL, puis TLS/copie vérifiée identiques."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import secrets
import shutil
import statistics
import subprocess
import tempfile
import threading
import time

from ultra.engine import LocalSource, Transfer
from ultra.invitation import read_invitation, write_invitation
from ultra.network import make_server
from ultra.share_setup import prepare_share


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rounds',type=int,default=6)
    parser.add_argument('--output',default='reports/share-setup-0.3.5.json')
    args=parser.parse_args()
    if not 2<=args.rounds<=8: parser.error('2–8 répétitions')
    if not shutil.which('openssl'): parser.error('OpenSSL CLI pour la référence seulement')
    import cryptography
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import hashes,serialization
    raw=[]
    with tempfile.TemporaryDirectory(prefix='ultra-setup-bench-') as temp:
        root=Path(temp);src=root/'source';src.mkdir()
        rng=random.Random(9189)
        (src/'gros été.bin').write_bytes(rng.randbytes(8*1024*1024))
        for i in range(128): (src/f'petit{i:03}.bin').write_bytes(rng.randbytes(2048))
        (src/'.caché').write_bytes(b'hidden');(src/'vide').touch();(src/'dossier vide').mkdir()
        expected={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir() if p.is_file()}
        for iteration in range(args.rounds):
            order=['manual_openssl','automatic']
            if iteration%2:order.reverse()
            for mode in order:
                directory=root/f'config-{iteration}-{mode}'
                started=time.perf_counter()
                if mode=='automatic':
                    prepare_share('https://localhost:8443',directory)
                else:
                    directory.mkdir(mode=0o700)
                    subprocess.run(['openssl','req','-x509','-newkey','rsa:3072','-nodes',
                        '-keyout',str(directory/'server-key.pem'),'-out',str(directory/'server-cert.pem'),
                        '-days','7','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],
                        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    token=secrets.token_urlsafe(48)
                    with (directory/'token.txt').open('w') as f:f.write(token);f.flush();os.fsync(f.fileno())
                    write_invitation('https://localhost:8443',directory/'server-cert.pem',directory/'token.txt',directory/'acces.utconnect')
                setup_seconds=time.perf_counter()-started
                token=(directory/'token.txt').read_text()
                server=make_server(LocalSource(src),('127.0.0.1',0),directory/'server-cert.pem',directory/'server-key.pem',token,'none')
                # Certificate SAN is independent of port. Export actual port after bind;
                # both variants include this extra ephemeral-test export in total time.
                actual=directory/'actual.utconnect'
                write_invitation(f'https://localhost:{server.server_port}',directory/'server-cert.pem',directory/'token.txt',actual)
                prepared_seconds=time.perf_counter()-started
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    transfer_start=time.perf_counter()
                    dest=root/f'destination-{iteration}-{mode}'
                    result=Transfer(read_invitation(actual).remote_source('none'),dest).run()
                    transfer_seconds=time.perf_counter()-transfer_start
                    total_seconds=time.perf_counter()-started
                    if result.errors:raise RuntimeError(result.errors)
                    for name,sha in expected.items():
                        if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('Independent SHA mismatch')
                    if not (dest/'dossier vide').is_dir():raise RuntimeError('Empty directory lost')
                    raw.append(dict(mode=mode,round=iteration,setup_seconds=setup_seconds,prepared_seconds=prepared_seconds,
                        transfer_seconds=transfer_seconds,total_seconds=total_seconds,files=result.files,bytes=result.bytes,independent_verified=True))
                    print(mode,iteration,setup_seconds,total_seconds,flush=True)
                    shutil.rmtree(dest)
                finally:
                    server.shutdown();server.server_close();thread.join(timeout=5)
    summary={mode:{key:statistics.median(row[key] for row in raw if row['mode']==mode)
             for key in ('setup_seconds','prepared_seconds','transfer_seconds','total_seconds')}
             for mode in ('manual_openssl','automatic')}
    output=dict(platform=platform.platform(),cryptography=cryptography.__version__,rounds=args.rounds,
        measurement='Linux warm-cache loopback TLS, no bandwidth limit, raw transport. 8 MiB + 128 x 2 KiB, hidden/empty files and empty directory. RSA3072 key/certificate, secret generation/files+fsync and invitation export included in setup. Total also includes server inventory/hash/TLS configuration, ephemeral-test second export, client import/TLS/copy/fsync/reconstruction/engine checks. Dataset creation, dependency installation/import warmup, user actions and independent extra final SHA check excluded. Not installation, Windows ACL, RDP, USB or Internet. No compression change. RSA key-generation variance can dominate.',raw=raw,median_seconds=summary)
    Path(args.output).write_text(json.dumps(output,indent=2),encoding='utf-8')


if __name__=='__main__':main()
