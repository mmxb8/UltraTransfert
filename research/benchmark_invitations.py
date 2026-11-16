"""Comparaison bornée : client 0.3.3 manuel et invitation courante en HTTPS local."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time

from ultra.engine import LocalSource
from ultra.invitation import write_invitation
from ultra.network import make_server

CLIENT = '''import hashlib,json,pathlib,sys,time
from ultra.engine import Transfer
from ultra.network import RemoteSource,read_token
start=time.perf_counter()
if sys.argv[1]=='invitation':
 from ultra.invitation import read_invitation
 source=read_invitation(sys.argv[2]).remote_source('none')
else:
 source=RemoteSource(sys.argv[2],read_token(sys.argv[3]),sys.argv[4],'none')
r=Transfer(source,sys.argv[5]).run()
elapsed=time.perf_counter()-start
if r.errors: raise RuntimeError(r.errors)
expected=json.loads(pathlib.Path(sys.argv[6]).read_text())
for name,sha in expected['files'].items():
 if hashlib.sha256((pathlib.Path(sys.argv[5])/name).read_bytes()).hexdigest()!=sha: raise RuntimeError('Independent SHA mismatch')
for name in expected['directories']:
 if not (pathlib.Path(sys.argv[5])/name).is_dir(): raise RuntimeError('Missing directory')
print(json.dumps(dict(seconds=elapsed,files=r.files,bytes=r.bytes,independent_verified=True)))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--output', default='reports/invitation-https-0.3.4.json')
    args = parser.parse_args()
    if not 3 <= args.rounds <= 9:
        parser.error('3–9 répétitions')
    current = Path(__file__).resolve().parents[1]
    reference = Path(args.reference).resolve()
    if not (reference/'ultra/network.py').is_file():
        parser.error('Référence source absente')
    if not shutil.which('openssl'):
        parser.error('OpenSSL CLI requis pour les certificats de ce banc seulement')
    raw = []
    with tempfile.TemporaryDirectory(prefix='ultra-invitation-bench-') as temp:
        root = Path(temp); src = root/'source'; src.mkdir()
        rng = random.Random(9188)
        for i in range(128):
            (src/f'petit_{i:03}_été.bin').write_bytes(rng.randbytes(2048))
        (src/'gros.bin').write_bytes(rng.randbytes(16*1024*1024))
        (src/'.caché').write_bytes(b'cache'); (src/'vide').touch(); (src/'dossier vide').mkdir()
        expected = root/'expected.json'
        expected.write_text(json.dumps({'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.iterdir() if p.is_file()},'directories':['dossier vide']}))
        cert, key = root/'cert.pem', root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        tokenfile=root/'token.txt';tokenfile.write_text('benchmark-invitation-'+('x'*48))
        started=time.perf_counter()
        server=make_server(LocalSource(src),('127.0.0.1',0),cert,key,tokenfile.read_text(),'none')
        preparation=time.perf_counter()-started
        url=f'https://localhost:{server.server_port}'
        invite=root/'accès.utconnect'
        started=time.perf_counter();write_invitation(url,cert,tokenfile,invite)
        export_seconds=time.perf_counter()-started
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for iteration in range(args.rounds):
                order=list(itertools.permutations(['manual_reference','manual_current','invitation']))[iteration % 6]
                for mode in order:
                    dest=root/f'dest-{iteration}-{mode}'
                    proc=subprocess.run([sys.executable,'-c',CLIENT,mode,str(invite) if mode=='invitation' else url,str(tokenfile),str(cert),str(dest),str(expected)],cwd=reference if mode=='manual_reference' else current,check=True,capture_output=True,text=True)
                    row={'mode':mode,'round':iteration,**json.loads(proc.stdout)};raw.append(row)
                    print(mode,iteration,row['seconds'],flush=True)
                    shutil.rmtree(dest)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
    summary={mode:statistics.median(row['seconds'] for row in raw if row['mode']==mode) for mode in ('manual_reference','manual_current','invitation')}
    result={'platform':platform.platform(),'python':platform.python_version(),'measurement':'Synthetic warm-cache TLS loopback, no bandwidth limit. 128 x 2 KiB, one 16 MiB, hidden/empty files and empty directory. Client invitation read/parse and TLS+manifest+copy/fsync+reconstruction+engine verification included. Independent final SHA check excluded from duration. Certificate/dataset generation excluded; shared server preparation and one-time invitation export reported separately. Not Windows/RDP/physical USB or Internet. No compression changed.','server_prepare_seconds':preparation,'invitation_export_seconds':export_seconds,'rounds':args.rounds,'raw':raw,'median_seconds':summary}
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
