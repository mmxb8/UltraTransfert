"""Comparaison processus isolés, TLS loopback, caches chauds ; pas de réseau physique."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time


def child(root, source, destination, cert, key, workers, compression):
    sys.path.insert(0, root)
    from ultra.engine import LocalSource, Transfer, Options, digest
    from ultra.network import make_server, RemoteSource
    start, cpu = time.perf_counter(), time.process_time()
    server = make_server(LocalSource(source), ('127.0.0.1', 0), cert, key, 'x'*48, compression)
    accepted = [0]
    original = server.get_request
    def get_request():
        result = original()
        accepted[0] += 1
        return result
    server.get_request = get_request
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        remote = RemoteSource(f'https://localhost:{server.server_port}', 'x'*48, cert, compression)
        result = Transfer(remote, destination, Options(workers=workers)).run()
        elapsed, cpu_elapsed = time.perf_counter()-start, time.process_time()-cpu
        if result.errors:
            raise RuntimeError(result.errors)
        for p in Path(source).rglob('*'):
            if p.is_file():
                assert digest(p) == digest(Path(destination)/p.relative_to(source))
        return dict(seconds=elapsed, cpu_seconds=cpu_elapsed, max_rss_kib=int(next(line.split()[1] for line in Path("/proc/self/status").read_text().splitlines() if line.startswith("VmHWM:"))),
                    tls_connections=accepted[0], files=result.files, bytes=result.bytes)
    finally:
        server.shutdown(); server.server_close(); thread.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline'); parser.add_argument('--candidate'); parser.add_argument('--output')
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--large-mib',type=int,default=32)
    parser.add_argument('--modes',nargs='+',choices=['none','auto','gzip','ultra'],default=['none','auto','gzip','ultra'])
    parser.add_argument('--workloads',nargs='+',choices=['small','large'],default=['small','large'])
    parser.add_argument('--child', nargs=8)
    args = parser.parse_args()
    if args.child:
        root, source, dest, cert, key, workers, compression, unused = args.child
        print(json.dumps(child(root, source, dest, cert, key, int(workers), compression)))
        return
    if not 1 <= args.rounds <= 15 or not 1 <= args.large_mib <= 1024:
        parser.error('1–15 répétitions, 1–1024 Mio')
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp); cert, key = base/'cert.pem', base/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        workloads = {}
        for name in args.workloads:
            src = base/name; src.mkdir(); (src/'vide').mkdir(); (src/'.caché').write_bytes(b'')
            if name == 'small':
                for i in range(160): (src/f'été-{i}.bin').write_bytes(bytes([i])*1024)
            else:
                rng = random.Random(42)
                with (src/'grand').open('wb') as stream:
                    for _ in range(args.large_mib): stream.write(rng.randbytes(1024*1024))
            workloads[name] = src
        jobs = [(name, version, workers, compression, run) for name in workloads for version in ('baseline','candidate') for workers in (1,4) for compression in args.modes for run in range(args.rounds)]
        random.Random(23).shuffle(jobs)
        rows = []
        for i,(name,version,workers,compression,run) in enumerate(jobs):
            row = json.loads(subprocess.check_output([sys.executable, str(Path(__file__).resolve()), '--child', str(Path(getattr(args,version)).resolve()),str(workloads[name]),str(base/f'dest-{i}'),str(cert),str(key),str(workers),compression,'unused'], text=True))
            rows.append(dict(workload=name, version=version, workers=workers, compression=compression, run=run, **row))
            Path(args.output+".partial").write_text(json.dumps(rows,indent=2))
            shutil.rmtree(base/f"dest-{i}")
        summary = []
        for name in workloads:
            for version in ('baseline','candidate'):
                for workers in (1,4):
                    for compression in args.modes:
                        subset = [r for r in rows if (r['workload'],r['version'],r['workers'],r['compression'])==(name,version,workers,compression)]
                        summary.append(dict(workload=name,version=version,workers=workers,compression=compression, **{k:statistics.median(r[k] for r in subset) for k in ('seconds','cpu_seconds','max_rss_kib','tls_connections')}))
        Path(args.output).write_text(json.dumps(dict(environment=sys.version, limits='TLS Linux loopback; caches chauds; total inclut inventaires/hachages, préparation serveur, TLS, copie et vérification; exclut génération corpus/certificat, import et contrôle indépendant supplémentaire; RSS processus complet en Kio, CPU client+serveur',rows=rows,summary=summary),indent=2))
        Path(args.output+".partial").unlink(missing_ok=True)
        print(json.dumps(summary,indent=2))

if __name__ == '__main__': main()
