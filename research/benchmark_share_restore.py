"""Nouvelle préparation vs réouverture sauvegardée : cycle TLS vérifié complet."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import random
import shutil
import socket
import statistics
import tempfile
import time

from ultra.engine import Transfer
from ultra.invitation import read_invitation
from ultra.share_setup import prepare_share
from ultra.share_restore import load_prepared_share
from ultra.share_session import ShareSession


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rounds',type=int,default=6)
    parser.add_argument('--output',default='reports/share-restore-0.3.7.json')
    args=parser.parse_args()
    if not 2<=args.rounds<=8:parser.error('2–8 répétitions')
    raw=[]
    with tempfile.TemporaryDirectory(prefix='ultra-restore-bench-') as temp:
        root=Path(temp);src=root/'source';src.mkdir()
        rng=random.Random(9191)
        (src/'gros été.bin').write_bytes(rng.randbytes(8*1024*1024))
        for i in range(128):(src/f'petit{i:03}.bin').write_bytes(rng.randbytes(2048))
        (src/'.caché').write_bytes(b'hidden');(src/'vide').touch();(src/'dossier vide').mkdir()
        expected={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir() if p.is_file()}
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
        url=f'https://localhost:{port}'
        started=time.perf_counter();saved=prepare_share(url,root/'saved')
        initial_saved_setup_seconds=time.perf_counter()-started
        for iteration in range(args.rounds):
            order=['fresh','restored']
            if iteration%2:order.reverse()
            for mode in order:
                started=time.perf_counter()
                selected=(prepare_share(url,root/f'fresh-{iteration}') if mode=='fresh'
                          else load_prepared_share(saved.directory))
                connection_seconds=time.perf_counter()-started
                session=ShareSession()
                try:
                    session.start(src,selected)
                    ready_seconds=time.perf_counter()-started
                    dest=root/f'dest-{mode}-{iteration}'
                    result=Transfer(read_invitation(selected.invitation_path).remote_source(),dest).run()
                    if result.errors:raise RuntimeError(result.errors)
                    session.stop()
                    total_seconds=time.perf_counter()-started
                    for name,sha in expected.items():
                        if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('Independent SHA mismatch')
                    if not (dest/'dossier vide').is_dir():raise RuntimeError('Missing directory')
                    raw.append(dict(mode=mode,round=iteration,connection_seconds=connection_seconds,
                        ready_seconds=ready_seconds,total_seconds=total_seconds,files=result.files,bytes=result.bytes,independent_verified=True))
                    print(mode,iteration,connection_seconds,total_seconds,flush=True)
                    shutil.rmtree(dest)
                finally:session.stop()
    summary={mode:{key:statistics.median(row[key] for row in raw if row['mode']==mode)
        for key in ('connection_seconds','ready_seconds','total_seconds')} for mode in ('fresh','restored')}
    import cryptography
    output=dict(platform=platform.platform(),cryptography=cryptography.__version__,rounds=args.rounds,
        initial_saved_setup_seconds=initial_saved_setup_seconds,
        measurement='Linux warm-cache synthetic loopback TLS, no bandwidth limit. 8 MiB + 128 x 2 KiB + hidden/empty files and empty directory. Same current server/client/auto compression, random data not selecting gzip. Fresh includes RSA3072 key/cert/token/invitation generation and writes; restored reuses prior saved connection and includes bounds/permissions/authentication/offline TLS validation. Total includes connection step, source inventory/hash/server preparation, repeated pre-listen validation, TLS transfer/copy/fsync/reconstruction/engine checks and stop. Prior initial saved setup reported separately and excluded from the restart column by design. Dataset creation, dependency installation/import startup, UI/user actions and independent extra final SHA check excluded. Not a throughput/codec innovation claim, not Windows/RDP/USB or Internet.',raw=raw,median_seconds=summary)
    Path(args.output).write_text(json.dumps(output,indent=2),encoding='utf-8')


if __name__=='__main__':main()
