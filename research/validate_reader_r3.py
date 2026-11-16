"""Unpaced TLS integrity stress, not a performance comparison or Windows test."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import random
import secrets
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch

from research.budget_compression import BudgetEncoder
from research.stream_reader_r3 import LeanBlockReader,raw_view_unframe
from ultra.engine import LocalSource,Options,Transfer,digest
from ultra.network import RemoteSource,make_server


def main():
    with tempfile.TemporaryDirectory(prefix='ultra-r3-stress-') as tmp:
        root=Path(tmp);src=root/'source';src.mkdir();dst=root/'received'
        (src/'dossier vide été').mkdir();(src/'.caché').write_bytes(b'hidden')
        rng=random.Random(774532)
        chunk=rng.randbytes(4*1024*1024);expected=hashlib.sha256()
        with (src/'grand été.bin').open('wb') as f:
            for _ in range(256):f.write(chunk);expected.update(chunk)
        for i in range(512):
            (src/f'petit été-{i:04d}.bin').write_bytes(b'' if i%17==0 else rng.randbytes(2048))
        cert=root/'cert.pem';key=root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),
                        '-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        token=secrets.token_urlsafe(48)
        server=make_server(LocalSource(src),('127.0.0.1',0),cert,key,token,'ultra',link_mbps=1000)
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        stop=threading.Event();t=time.perf_counter()
        try:
            with ExitStack() as stack:
                stack.enter_context(patch('ultra.network.AdaptiveEncoder',side_effect=lambda *a,**kw:BudgetEncoder(1000)))
                stack.enter_context(patch('ultra.network.BlockReader',LeanBlockReader))
                stack.enter_context(patch('ultra.blockstream.unframe',raw_view_unframe))
                remote=RemoteSource(f'https://localhost:{server.server_port}',token,cert,'ultra')
                first=Transfer(remote,dst,Options(workers=1,buffer_size=65536),cancel=stop,
                               progress=lambda n,total:stop.set() if n>=1024*1024 else None).run()
                assert first.errors,'Interruption not observed'
                result=Transfer(remote,dst,Options(workers=2,buffer_size=1048576)).run()
                assert not result.errors,result.errors
                assert result.resumed_bytes>0,'No reused bytes'
                remote.release_connections()
                assert digest(dst/'grand été.bin')==expected.hexdigest()
                source_files={p.relative_to(src):p for p in src.rglob('*') if p.is_file()}
                dest_files={p.relative_to(dst):p for p in dst.rglob('*') if p.is_file() and '.ultra' not in p.relative_to(dst).parts[0]}
                # Engine's internal state directory is excluded explicitly below.
                from ultra.engine import STATE
                dest_files={rel:p for rel,p in dest_files.items() if rel.parts[0]!=STATE}
                assert set(source_files)==set(dest_files),(set(dest_files)-set(source_files))
                for rel,p in source_files.items():assert digest(p)==digest(dest_files[rel]),str(rel)
                assert (dst/'dossier vide été').is_dir()
                report={'large_bytes':(src/'grand été.bin').stat().st_size,'large_sha256':expected.hexdigest(),
                        'source_files':len(source_files),'empty_files':sum(p.stat().st_size==0 for p in source_files.values()),
                        'resumed_bytes':result.resumed_bytes,'elapsed_seconds_including_extra_hashes':time.perf_counter()-t,
                        'scope':'Real authenticated TLS loopback under Linux, unpaced, cached container filesystem; 1-GiB file built from repeated random 4-MiB chunks, 512 small files, Unicode/hidden/empty files and directory. Interrupt/resume, independent complete inventory and SHA256 checks. Not a throughput comparison, physical device or Windows/RDP validation.',
                        'server_metrics':dict(server.transfer_metrics),'status':'passed'}
                Path('reports/reader-r3-stress.json').write_text(json.dumps(report,indent=2)+'\n')
                print(json.dumps(report),flush=True)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':main()
