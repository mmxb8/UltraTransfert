"""Comparaison alternée de deux versions, mêmes données et réglages auto."""
import argparse
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time

from benchmark import datasets

CODE = '''import json, sys, time
from ultra.engine import LocalSource, Transfer
start=time.perf_counter()
r=Transfer(LocalSource(sys.argv[1]),sys.argv[2]).run()
if r.errors: raise RuntimeError(r.errors)
print(json.dumps({"seconds":time.perf_counter()-start,"bytes":r.bytes,"files":r.files}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--output", default="reports/comparison.json")
    args = parser.parse_args()
    if not 3 <= args.rounds <= 15:
        parser.error("3 à 15 répétitions")
    roots = {"reference": Path(args.reference).resolve(), "candidate": Path(__file__).resolve().parent}
    raw = []
    with tempfile.TemporaryDirectory(prefix="ultra-compare-") as tmp:
        root = Path(tmp)
        sources = datasets(root)
        rng = random.Random(886)
        for workload, source in sources.items():
            for iteration in range(args.rounds):
                order = list(roots)
                rng.shuffle(order)
                for name in order:
                    dest = root/f"dest-{workload}-{iteration}-{name}"
                    proc = subprocess.run([sys.executable, "-c", CODE, str(source), str(dest)], cwd=roots[name], text=True, capture_output=True, check=True)
                    row = {"workload": workload, "version": name, "round": iteration, **json.loads(proc.stdout)}
                    raw.append(row)
                    import shutil
                    shutil.rmtree(dest)
    summary = []
    for workload in sources:
        medians = {v: statistics.median(r["seconds"] for r in raw if r["workload"] == workload and r["version"] == v) for v in roots}
        summary.append({"workload": workload, "median_seconds": medians,
                        "gain_percent": (1-medians["candidate"]/medians["reference"])*100})
    data = {"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rounds": args.rounds,
            "method": "Paired randomized order, separate processes, same synthetic data, warm cache, auto workers, all SHA-256 verification and requested fsync included. Local environment only; not USB, Windows or Internet throughput.",
            "summary": summary, "raw": raw}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
