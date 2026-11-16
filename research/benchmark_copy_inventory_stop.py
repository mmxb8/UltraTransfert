"""Comparer l'arrêt du contrôleur avant/après, widgets doublés, inventaire réel."""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

import ultra.engine as engine
from ultra.gui import App


def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root/'tests'))
    from test_ui_workflow import WorkflowTests
    spec = importlib.util.spec_from_file_location('ultra.gui_reference', root/'history/v0.3.14/ultra/gui.py')
    old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    rows = []
    with tempfile.TemporaryDirectory(prefix='ultra-inventory-stop-') as tmp:
        src = Path(tmp)/'source'; src.mkdir()
        for i in range(3000): (src/f'été_日本語_{i}').write_bytes(b'unchanged')
        real = engine.check_cancel
        for repeat in range(6):
            order = ('reference', 'current') if repeat % 2 == 0 else ('current', 'reference')
            for version in order:
                helper = WorkflowTests(); dst = Path(tmp)/f'dest-{repeat}-{version}'
                app = helper.make_app(src, dst); state = {'calls': 0, 'requested_at': None}
                def checkpoint(cancel):
                    state['calls'] += 1
                    if state['calls'] == 20:
                        state['requested_at'] = time.perf_counter(); app.request_stop()
                    real(cancel)
                started = time.perf_counter()
                with patch.object(engine, 'check_cancel', checkpoint):
                    (old.App if version == 'reference' else App).start(app)
                    terminal, error = helper.finish(app)
                ended = time.perf_counter()
                assert terminal[0] == 'stopped'; error.assert_not_called()
                if version == 'current': assert not dst.exists()
                rows.append(dict(version=version, repeat=repeat, checkpoints=state['calls'],
                                 controller_seconds=ended-started,
                                 after_stop_seconds=ended-state['requested_at'],
                                 destination_created=dst.exists()))
        assert len(list(src.iterdir())) == 3000
        assert all(p.read_bytes() == b'unchanged' for p in src.iterdir())
    summary = {v: {k: statistics.median(r[k] for r in rows if r['version'] == v)
                   for k in ('checkpoints', 'controller_seconds', 'after_stop_seconds')}
               for v in ('reference', 'current')}
    report = dict(scope='Linux, real inventory of 3000 synthetic tiny Unicode files; warm caches, six alternating rounds. Stop at checkpoint 20. Controller and widgets doubled, no visual rendering or Windows/RDP; not a copy throughput benchmark. Source bytes checked after all rounds. Destination absent after current cancelled preparation.',
                  summary=summary, rows=rows)
    (root/'reports/copy-inventory-stop-0.3.15.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
