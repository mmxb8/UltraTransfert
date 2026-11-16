"""Independent validation inputs, not used to tune R2.2.

Local real bytes are NOT an external downloaded corpus. Paths/hashes are kept
in the output; reruns require the same OS packages for exact reproduction.
Usage: python -m research.benchmark_budget_validation cpu [CPU harness args]
       python -m research.benchmark_budget_validation https [HTTPS harness args]
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

from research import benchmark_predictive as cpu
from research import benchmark_predictive_https as https


def validation_datasets():
    rng=random.Random(9912007)
    n=2*1024*1024
    # Different frequency, mixed smooth/stepped components and random noise.
    numeric=b''.join(struct.pack('<f',3*math.cos(i*.00217)+(i//901)%7+rng.uniform(-.001,.001))
                     for i in range(n//4))
    paths={'actual_openssl_executable':Path('/usr/bin/openssl'),
           'actual_dejavu_font':Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
           'actual_transfer_engine_source':Path('ultra/engine.py')}
    data={name:path.read_bytes() for name,path in paths.items()}
    data['float32_noisy_validation']=numeric
    data['gzip_independent_noise']=gzip.compress(rng.randbytes(n),compresslevel=1,mtime=0)
    return data


def main():
    phase=sys.argv.pop(1)
    if phase not in ('cpu','https'):
        raise SystemExit('Expected cpu or https')
    cpu.datasets=validation_datasets
    https.datasets=validation_datasets
    (cpu if phase=='cpu' else https).main()


if __name__=='__main__':main()
