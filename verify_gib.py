"""Test d'intégration explicite de 1 Gio (données synthétiques, caches chauds)."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import random
import tempfile
import time

from ultra.engine import LocalSource, Transfer, digest


def main():
    with tempfile.TemporaryDirectory(prefix="ultra-gib-") as tmp:
        root = Path(tmp)
        src, dst = root/"source", root/"destination"
        src.mkdir()
        block = random.Random(901).randbytes(4*1024*1024)
        reference = hashlib.sha256()
        with open(src/"un-gib.bin", "wb") as f:
            for _ in range(256):
                f.write(block)
                reference.update(block)
            f.flush()
            os.fsync(f.fileno())
        started = time.perf_counter()
        result = Transfer(LocalSource(src), dst).run()
        wall = time.perf_counter()-started
        if result.errors or digest(dst/"un-gib.bin") != reference.hexdigest():
            raise RuntimeError(result.errors or "Empreinte indépendante différente")
        report = {"size_bytes": 1073741824, "wall_seconds": wall, "logical_MBps": 1073741824/wall/1e6, "independent_sha256": reference.hexdigest(), "measurement": "Synthetic repeated pseudo-random block; warm cache; fsync requested; full verification included in wall time. Not physical disk/USB or Internet throughput.", "result": asdict(result)}
        Path("reports/one-gib.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "result"}, indent=2))


if __name__ == "__main__":
    main()
