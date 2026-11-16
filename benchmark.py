"""Mesures synthétiques avec caches chauds ; pas une certification disque/USB."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import tempfile
import time

from ultra.engine import LocalSource, Options, Transfer


def datasets(root, scale=1):
    small = root/"small"
    large = root/"large"
    small.mkdir()
    large.mkdir()
    rng = random.Random(80642)
    block = rng.randbytes(1024*1024)
    for i in range(800):
        (small/f"fichier-{i:04}.bin").write_bytes(block[:(i%16+1)*128])
    for name, size, data in (("pseudo-random.bin", 256*scale, block), ("compressible.bin", 64*scale, b"A"*1024*1024)):
        with (large/name).open("wb") as f:
            for _ in range(size):
                f.write(data)
            f.flush()
            os.fsync(f.fileno())
    return {"small_800_files": small, "large_320MiB": large}


def benchmark(output, rounds=3, native=True):
    configurations = {
        "python_w4_b4MiB": Options(workers=4, buffer_size=4*1024*1024),
        "python_w2_b1MiB": Options(workers=2, buffer_size=1024*1024),
        "python_w1_b1MiB": Options(workers=1, buffer_size=1024*1024),
        "python_auto_b1MiB": Options(),
    }
    binary = Path(__file__).resolve().parent/"bin"/("ultra_native.exe" if os.name == "nt" else "ultra_native")
    if native and binary.exists():
        configurations["native_w4_b4MiB"] = Options(workers=4, buffer_size=4*1024*1024, native=str(binary))
    results = []
    with tempfile.TemporaryDirectory(prefix="ultra-bench-") as tmp:
        root = Path(tmp)
        sources = datasets(root)
        jobs = [(workload, config, i) for workload in sources for config in configurations for i in range(rounds)]
        random.Random(1467).shuffle(jobs)
        for workload, name, iteration in jobs:
            destination = root/"destination"
            started = time.perf_counter()
            result = Transfer(LocalSource(sources[workload]), destination, configurations[name]).run()
            elapsed = time.perf_counter()-started
            if result.errors:
                raise RuntimeError(result.errors)
            results.append({"workload": workload, "configuration": name, "round": iteration, "seconds": elapsed, "logical_MBps": result.bytes/elapsed/1e6, "bytes": result.bytes, "files": result.files, "file_work_seconds": result.file_work_seconds, "final_verify_seconds": result.final_verify_seconds})
            print(f"{workload} {name} #{iteration+1} : {elapsed:.4f} s", flush=True)
            shutil.rmtree(destination)
    summary = []
    for workload in sources:
        for name in configurations:
            times = [r["seconds"] for r in results if r["workload"] == workload and r["configuration"] == name]
            summary.append({"workload": workload, "configuration": name, "median_seconds": statistics.median(times), "min_seconds": min(times), "max_seconds": max(times), "cv": statistics.stdev(times)/statistics.mean(times) if len(times)>1 else 0})
    report = {"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "platform": platform.platform(), "python": platform.python_version(), "measurement": "Synthetic warm-cache local copies. SHA-256 during copy, temporary-file reread and final published-file reread included. fsync requested. No cold-cache, physical USB, Internet or power-loss claim. Logical input bytes per wall second, not physical bus throughput. Dataset repeats a deterministic pseudo-random 1MiB block; no compression in these local trials.", "configurations": {k: asdict(v) for k, v in configurations.items()}, "rounds": rounds, "raw": results, "summary": summary}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="reports/benchmark.json")
    p.add_argument("--rounds", type=int, default=3)
    a = p.parse_args()
    benchmark(a.output, a.rounds)
