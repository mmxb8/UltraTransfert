"""Independent held-out scaling study using the same authenticated TLS harness."""
import json
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile

def main():
    methods=['bundle-auto-mdeflate-r42','bundle-auto-mdeflate','tar-zstd1','zip-deflate']
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);rng=random.Random(98766121)
        for count in (64,256,1024,3840):
            src=root/str(count);src.mkdir();(src/'vide').mkdir();(src/'.caché').write_bytes(b'')
            for i in range(count):
                data=(f'route-{i%23}: inventory update {i}\n'.encode()*32) if i%3==0 else rng.randbytes(144+i%17)
                (src/f'élément-{i:04}').write_bytes(data)
        cert,key=root/'cert.pem',root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),
          '-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],
          check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        jobs=[(count,method,i) for count in (64,256,1024,3840) for method in methods for i in range(5)]
        random.Random(991221).shuffle(jobs)
        for j,(count,method,i) in enumerate(jobs):
            out=root/f'job-{j}'
            row=json.loads(subprocess.check_output([sys.executable,'-m','research.benchmark_bundle_r4',
                   '--child',str(root/str(count)),str(out),str(cert),str(key),method,'1000','unused'],text=True))
            row.update(count=count,method=method,round=i);rows.append(row);shutil.rmtree(out)
            if j%10==0: print(f'{j+1}/{len(jobs)} verified',flush=True)
    summary=[]
    for count in (64,256,1024,3840):
        for method in methods:
            selected=[r for r in rows if (r['count'],r['method'])==(count,method)]
            summary.append(dict(count=count,method=method,
                **{'median_'+k:statistics.median(v[k] for v in selected) for k in
                   ('seconds','cpu_seconds','max_rss_kib','restore_seconds','http_plaintext_bytes')},
                min_seconds=min(v['seconds'] for v in selected),max_seconds=max(v['seconds'] for v in selected)))
    Path('reports/bundle-r43-scaling.json').write_text(json.dumps(dict(platform=platform.platform(),
      scope='Held-out seed 98766121. Files below 2 KiB, mixed random/structured, Unicode/hidden/empty directory. Extra hidden empty file not included in count label. Same full TLS harness and integrity guarantees/caveats as bundle-r43-final.json. Five randomized repetitions, isolated children, warm local caches, 1000 Mbit/s application pacing. Not physical network or RDP.',summary=summary,raw=rows),indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
