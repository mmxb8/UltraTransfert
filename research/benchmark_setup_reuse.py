"""Préparation répétée, complément déjà présent ; pip réel forcé hors ligne."""
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

import prepare_installation as current


def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root/'tests'))
    import test_installation as fixtures
    from test_installation_reuse import attach_dependencies
    spec = importlib.util.spec_from_file_location('setup_reference', root/'history/v0.3.15/prepare_installation.py')
    old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    real = subprocess.run
    rows = []
    with fixtures.InstallationTests().project() as project:
        assert current.prepare(project, offline=True)['core_ready']
        attach_dependencies(project)
        # Création commune/fixtures exclues. Le pip importable du banc est réutilisé.
        for repeat in range(6):
            for version in (('old', 'new') if repeat % 2 == 0 else ('new', 'old')):
                module = old if version == 'old' else current
                commands = []
                def run(args, **kw):
                    args = list(args)
                    if '-m' in args and args[args.index('-m')+1] == 'pip' and 'install' in args:
                        args.insert(args.index('install')+1, '--no-index')
                    commands.append(args)
                    return real(args, **kw)
                started = time.perf_counter()
                with patch.object(module.subprocess, 'run', side_effect=run):
                    report = module.prepare(project)
                seconds = time.perf_counter()-started
                assert report['core_ready'] and report['sharing_ready'], report
                assert report['core_probe']['resumed_bytes'] > 0
                pip_calls = sum('-m' in a and a[a.index('-m')+1] == 'pip' for a in commands)
                if version == 'new': assert pip_calls == 0 and report['sharing_reused']
                rows.append(dict(repeat=repeat, version=version, seconds=seconds, pip_calls=pip_calls,
                                 core_resume_bytes=report['core_probe']['resumed_bytes']))
    summary = {v: dict(median_seconds=statistics.median(r['seconds'] for r in rows if r['version']==v),
                       min_seconds=min(r['seconds'] for r in rows if r['version']==v),
                       max_seconds=max(r['seconds'] for r in rows if r['version']==v)) for v in ('old', 'new')}
    output = dict(scope='Linux source preparation, existing venv, dependency fixture via .pth to installed cryptography 50.0.2 and CFFI paths. Real subprocesses/Tcl/copy/resume and pip. Pip install forced --no-index for reference, so no downloads/index/network latency measured. Common venv/fixture setup excluded; six alternating rounds, warm cache. No Windows scripts, EXE, visual launch or first installation measured.',
                  rows=rows, summary=summary)
    (root/'reports/setup-reuse-0.3.16.json').write_text(json.dumps(output, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
