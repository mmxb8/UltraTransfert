"""Démonstration reproductible : 1 Gio, un bloc de 4 Mio modifié, HTTPS local.

Mesure les octets fichier servis indépendamment côté serveur et vérifie les deux
copies finales. Aucun chiffre n'est présenté comme un débit Internet/USB réel.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import shutil
import subprocess
import tempfile
import threading
import time

from ultra.delta import DeltaSource
from ultra.engine import LocalSource, Transfer, digest
from ultra.network import RemoteSource, make_server


def main():
    block_size, total = 4*1024*1024, 1024*1024*1024
    with tempfile.TemporaryDirectory(prefix='ultra-delta-demo-') as tmp:
        root = Path(tmp)
        source, reference = root/'source', root/'reference'
        source.mkdir(); reference.mkdir()
        expected = hashlib.sha256()
        rng = random.Random(341908)
        with (source/'nouveau-nom.bin').open('wb') as out, (reference/'ancienne-copie.bin').open('wb') as old:
            for i in range(total//block_size):
                data = rng.randbytes(block_size)
                out.write(data); expected.update(data)
                if i == 107:
                    changed = bytearray(data); changed[99] ^= 1
                    old.write(changed)
                else:
                    old.write(data)
            out.flush(); old.flush(); os.fsync(out.fileno()); os.fsync(old.fileno())
        cert, key = root/'cert.pem', root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        token = secrets.token_urlsafe(48)
        start=time.perf_counter()
        server=make_server(LocalSource(source),('127.0.0.1',0),cert,key,token,'none',block_size)
        startup=time.perf_counter()-start
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'https://localhost:{server.server_port}'
        results={}
        try:
            for kind in ('full','delta'):
                start=time.perf_counter()
                remote=RemoteSource(url,token,cert,'none')
                origin=DeltaSource(remote,reference) if kind=='delta' else remote
                before=dict(server.transfer_metrics)
                result=Transfer(origin,root/kind).run()
                elapsed=time.perf_counter()-start
                if result.errors:
                    raise RuntimeError(result.errors)
                independent=digest(root/kind/'nouveau-nom.bin')
                if independent != expected.hexdigest():
                    raise RuntimeError('Independent SHA-256 mismatch')
                metrics={k:server.transfer_metrics[k]-before[k] for k in before}
                results[kind]={'client_seconds_including_manifest_and_reference_index':elapsed,
                               'server_metrics':metrics,'result':asdict(result),'independent_sha256':independent}
            assert results['full']['server_metrics']['file_payload_bytes']==total
            assert results['delta']['server_metrics']['file_payload_bytes']==block_size
            assert results['delta']['result']['delta']['reused_payload_bytes']==total-block_size
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
        data={'size_bytes':total,'block_size':block_size,'source_manifest_preparation_seconds':startup,
              'payload_reduction_percent':100*(1-block_size/total),'runs':results,
              'measurement':'One synthetic 1-GiB file with deterministic distinct pseudo-random 4-MiB blocks; one byte differs in one block in the reference, which has a different filename. HTTPS over loopback, warm caches, no compression. Server counters count uncompressed file body payload, not TLS/HTTP/manifest overhead. Client timing includes fetching the manifest, reference indexing for delta, complete destination write and integrity checks; excludes source preparation (reported separately) and the extra independent hash. One run per mode; no statistical speed claim or real Internet/USB throughput claim.'}
        Path('reports/delta-one-gib.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        print(json.dumps({'size_bytes':total,'payload_reduction_percent':data['payload_reduction_percent'],
                          'full_file_payload_bytes':results['full']['server_metrics']['file_payload_bytes'],
                          'delta_file_payload_bytes':results['delta']['server_metrics']['file_payload_bytes'],
                          'full_client_seconds':results['full']['client_seconds_including_manifest_and_reference_index'],
                          'delta_client_seconds':results['delta']['client_seconds_including_manifest_and_reference_index'],
                          'independent_sha256':expected.hexdigest()},indent=2))


if __name__=='__main__':
    main()
