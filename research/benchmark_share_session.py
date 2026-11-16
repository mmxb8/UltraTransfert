"""Cycle de partage complet : orchestration directe vs contrôleur graphique sans écran."""
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
import threading
import time

from ultra.engine import LocalSource,Transfer
from ultra.invitation import write_invitation,read_invitation
from ultra.network import make_server,read_token
from ultra.share_setup import prepare_share,PreparedShare
from ultra.share_session import ShareSession


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rounds',type=int,default=6)
    parser.add_argument('--output',default='reports/share-session-0.3.6.json')
    args=parser.parse_args()
    if not 2<=args.rounds<=8:parser.error('2–8 répétitions')
    raw=[]
    with tempfile.TemporaryDirectory(prefix='ultra-session-bench-') as temp:
        root=Path(temp);src=root/'source';src.mkdir()
        rng=random.Random(9190)
        (src/'gros été.bin').write_bytes(rng.randbytes(16*1024*1024))
        for i in range(128):(src/f'petit{i:03}.bin').write_bytes(rng.randbytes(2048))
        (src/'.caché').write_bytes(b'hidden');(src/'vide').touch();(src/'dossier vide').mkdir()
        expected={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir() if p.is_file()}
        started=time.perf_counter();base=prepare_share('https://localhost:8443',root/'private')
        certificate_setup_seconds=time.perf_counter()-started
        for iteration in range(args.rounds):
            order=['direct','managed']
            if iteration%2:order.reverse()
            for mode in order:
                with socket.socket() as reserve:
                    reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
                url=f'https://localhost:{port}'
                path=root/f'invite-{iteration}-{mode}.utconnect'
                session=ShareSession();server=None;thread=None
                started=time.perf_counter()
                profile=write_invitation(url,base.directory/'server-cert.pem',base.directory/'token.txt',path)
                prepared=PreparedShare(base.directory,path,url,base.certificate_sha256)
                try:
                    if mode=='managed':session.start(src,prepared)
                    else:
                        server=make_server(LocalSource(src),('127.0.0.1',port),base.directory/'server-cert.pem',base.directory/'server-key.pem',read_token(base.directory/'token.txt'),'auto')
                        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.1),daemon=True);thread.start()
                    ready_seconds=time.perf_counter()-started
                    dest=root/f'dest-{iteration}-{mode}'
                    result=Transfer(read_invitation(path).remote_source(),dest).run()
                    if result.errors:raise RuntimeError(result.errors)
                    stop_started=time.perf_counter()
                    if mode=='managed':session.stop()
                    else:server.shutdown();server.server_close();thread.join(timeout=5)
                    stop_seconds=time.perf_counter()-stop_started
                    total_seconds=time.perf_counter()-started
                    for name,sha in expected.items():
                        if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('Independent SHA mismatch')
                    if not (dest/'dossier vide').is_dir():raise RuntimeError('Empty directory lost')
                    raw.append(dict(mode=mode,round=iteration,ready_seconds=ready_seconds,stop_seconds=stop_seconds,
                        total_seconds=total_seconds,bytes=result.bytes,files=result.files,independent_verified=True))
                    print(mode,iteration,total_seconds,stop_seconds,flush=True)
                    shutil.rmtree(dest)
                finally:
                    if session.active:session.stop()
                    if server is not None:
                        if thread is not None and thread.is_alive():server.shutdown()
                        server.server_close()
    summary={mode:{key:statistics.median(row[key] for row in raw if row['mode']==mode)
        for key in ('ready_seconds','stop_seconds','total_seconds')} for mode in ('direct','managed')}
    output=dict(platform=platform.platform(),rounds=args.rounds,certificate_setup_seconds=certificate_setup_seconds,
        measurement='Linux synthetic warm-cache loopback TLS, no bandwidth limit. 16 MiB + 128 x 2 KiB + hidden/empty files and empty directory. Same current server/client/auto compression in both variants (random payloads do not select gzip). Direct orchestration vs ShareSession controller, not old-vs-new-server benchmark. Total includes invitation export, source inventory/hash/TLS preparation, import/client/TLS/transport/copy/fsync/reconstruction/engine verification and stop. One-time key/certificate setup reported separately; dataset construction, dependency installation/import startup, GUI rendering and independent extra final SHA check excluded. No Windows/RDP/USB/Internet claim.',raw=raw,median_seconds=summary)
    Path(args.output).write_text(json.dumps(output,indent=2),encoding='utf-8')


if __name__=='__main__':main()
