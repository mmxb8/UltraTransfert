"""Un cycle reproductible et borné : compiler, tester, mesurer, recommander.

Les modifications de code restent effectuées et évaluées par la tâche planifiée.
Ce script ne prétend ni inventer des optimisations ni garantir des gains.
"""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from benchmark import benchmark


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--cycles", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.cycles <= 5 or not 3 <= args.rounds <= 15:
        parser.error("1–5 cycles et 3–15 répétitions ; pas de boucle infinie.")
    root = Path(__file__).resolve().parent
    os.chdir(root)
    lock = root/".cycle.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SystemExit("Un cycle détient déjà le verrou. Ne pas lancer de second processus.")
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        for i in range(args.cycles):
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())+f"-{i+1}"
            subprocess.run([sys.executable, "build.py"], check=True)
            with open(root/"reports"/f"tests-{stamp}.txt", "w", encoding="utf-8") as report:
                subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], stdout=report, stderr=subprocess.STDOUT, check=True)
            data = benchmark(root/"reports"/f"benchmark-{stamp}.json", args.rounds)
            summaries = {(s["workload"], s["configuration"]): s for s in data["summary"]}
            workloads = sorted({s["workload"] for s in data["summary"]})
            accepted = []
            for config in data["configurations"]:
                ratios = [summaries[(w, config)]["median_seconds"]/summaries[(w, "python_w4_b4MiB")]["median_seconds"] for w in workloads]
                score = math.prod(ratios)**(1/len(ratios))
                stable = all(summaries[(w, config)]["cv"] <= .15 for w in workloads)
                if score <= .92 and max(ratios) <= 1.10 and stable:
                    accepted.append({"configuration": config, "geometric_ratio": score, "worst_workload_ratio": max(ratios)})
            (root/"reports"/f"recommendation-{stamp}.json").write_text(json.dumps({"baseline": "python_w4_b4MiB", "candidates": sorted(accepted, key=lambda x: x["geometric_ratio"]), "policy": "Recommandation locale seulement : >=8% de gain géométrique, aucune charge >10% plus lente, CV <=15%. Aucune modification automatique des garanties d'intégrité. Valider sur le vrai matériel avant généralisation."}, indent=2), encoding="utf-8")
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
