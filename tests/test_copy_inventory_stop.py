"""Arrêt de préparation : contrôleur sans écran, inventaire et copie réels."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ultra.engine as engine
from ultra.engine import OperationCancelled, digest
import test_ui_workflow as workflow


class InventoryStopTests(unittest.TestCase):
    def fixture(self, root):
        src = root/'source'; src.mkdir()
        for i in range(80):
            (src/f'été_日本語_{i}').write_bytes(bytes([i])*1024)
        (src/'.caché').touch(); (src/'vide').mkdir()
        return src, root/'destination'

    def test_stop_during_real_inventory_then_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = self.fixture(Path(tmp))
            helper = workflow.WorkflowTests(); app = helper.make_app(src, dst)
            real = engine.check_cancel; calls = []
            def checkpoint(cancel):
                calls.append(cancel)
                if len(calls) == 12:
                    app.request_stop()
                real(cancel)
            with patch.object(engine, 'check_cancel', checkpoint):
                app.start(); terminal, error = helper.finish(app)
            self.assertEqual(terminal[0], 'stopped'); error.assert_not_called()
            self.assertTrue(all(c is app.cancel for c in calls))
            self.assertLess(len(calls), 80); self.assertFalse(dst.exists())
            self.assertIsNone(app.report_data)
            app.start(); terminal, error = helper.finish(app)
            self.assertEqual(terminal[0], 'done'); error.assert_not_called()
            self.assertEqual(app.report_data['files'], 81)
            self.assertTrue((dst/'vide').is_dir())
            for path in src.iterdir():
                if path.is_file(): self.assertEqual(digest(path), digest(dst/path.name))

    def test_stop_before_source_inventory_creates_no_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = self.fixture(Path(tmp)); helper = workflow.WorkflowTests()
            app = helper.make_app(src, dst); real = engine.LocalSource
            def source(path, cancel=None):
                app.request_stop()
                return real(path, cancel=cancel)
            with patch('ultra.gui.LocalSource', side_effect=source):
                app.start(); terminal, error = helper.finish(app)
            self.assertEqual(terminal[0], 'stopped'); error.assert_not_called()
            self.assertFalse(dst.exists())

    def test_real_permission_error_wins_over_stop(self):
        helper = workflow.WorkflowTests(); app = helper.make_app('source', 'dest')
        def source(*args, **kwargs):
            app.request_stop()
            raise PermissionError('Permission denied')
        with patch('ultra.gui.LocalSource', side_effect=source):
            app.start(); terminal, error = helper.finish(app)
        self.assertEqual(terminal[0], 'error'); error.assert_called_once()

    def test_unrequested_cancellation_is_not_announced_as_user_stop(self):
        helper = workflow.WorkflowTests(); app = helper.make_app('source', 'dest')
        with patch('ultra.gui.LocalSource', side_effect=OperationCancelled('annulation inattendue')):
            app.start(); terminal, error = helper.finish(app)
        self.assertEqual(terminal[0], 'error'); error.assert_called_once()

    def test_existing_destination_untouched_when_inventory_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = self.fixture(Path(tmp)); dst.mkdir(); (dst/'préexistant').write_bytes(b'keep')
            helper = workflow.WorkflowTests(); app = helper.make_app(src, dst)
            real = engine.check_cancel
            def checkpoint(cancel):
                app.request_stop(); real(cancel)
            with patch.object(engine, 'check_cancel', checkpoint):
                app.start(); terminal, error = helper.finish(app)
            self.assertEqual(terminal[0], 'stopped'); error.assert_not_called()
            self.assertEqual([p.name for p in dst.iterdir()], ['préexistant'])
            self.assertEqual((dst/'préexistant').read_bytes(), b'keep')
