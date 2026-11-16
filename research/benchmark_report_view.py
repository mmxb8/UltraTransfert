"""Comparer la préparation de l'ancien JSON et du bilan courant, sans Tk."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
import statistics
import tempfile
import time
import tracemalloc

from ultra.engine import Result
from ultra.report_view import capture_result, render_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=6)
    parser.add_argument('--output', type=Path, default=Path('reports/report-view-0.3.14.json'))
    args = parser.parse_args()
    if args.rounds < 2:
        parser.error('Au moins deux répétitions')
    rows = []
    with tempfile.TemporaryDirectory(prefix='ultra-report-view-') as tmp:
        report_path = Path(tmp)/'last-result.json'
        for count in (0, 1000, 100000):
            result = Result(files=count, directories=3, bytes=count*4096, copied=count,
                            seconds=1.25, hashes={f'été_日本語_{i}.bin': 'a'*64 for i in range(count)})
            # Même sérialisation que le rapport moteur ; fixtures, pas de copie de fichiers.
            report_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding='utf-8')
            original_size = report_path.stat().st_size
            report_path.read_text(encoding='utf-8')  # cache chaud explicite
            for repeat in range(args.rounds):
                order = ('old_json', 'current_summary') if repeat % 2 == 0 else ('current_summary', 'old_json')
                for variant in order:
                    tracemalloc.start()
                    started = time.perf_counter()
                    if variant == 'old_json':
                        text = report_path.read_text(encoding='utf-8')
                    else:
                        title, text = render_report(capture_result(result), 'done', 'destination été')
                        assert title == 'Copie terminée et vérifiée' and len(text) < 2000
                    elapsed = time.perf_counter()-started
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    rows.append(dict(files=count, repeat=repeat, variant=variant, seconds=elapsed,
                                     peak_bytes=peak, displayed_characters=len(text), technical_report_bytes=original_size))
                    del text
            assert report_path.stat().st_size == original_size
            assert len(result.hashes) == count
    summary = []
    for count in (0, 1000, 100000):
        for variant in ('old_json', 'current_summary'):
            selected = [r for r in rows if r['files'] == count and r['variant'] == variant]
            times = [r['seconds'] for r in selected]
            summary.append(dict(files=count, variant=variant, median_seconds=statistics.median(times),
                                min_seconds=min(times), max_seconds=max(times),
                                median_peak_bytes=statistics.median(r['peak_bytes'] for r in selected)))
    report = dict(platform=platform.platform(), python=platform.python_version(), rounds=args.rounds,
                  scope='Synthetic metadata only; warm local cache. Old path reads full JSON string, new path captures counters and formats current summary. Tracemalloc enabled. Fixture creation excluded. No Tk rendering, transfer throughput, network latency, Windows or RDP measurement.',
                  rows=rows, summary=summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
