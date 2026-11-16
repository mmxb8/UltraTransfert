"""Contrôleur sans écran : widgets doublés, moteur de fichiers réel."""
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from ultra.gui import App
from ultra.engine import Transfer, digest
from ultra.ui_feedback import outcome, error_action


class Value:
    def __init__(self, value=''):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class WorkflowTests(unittest.TestCase):
    def make_app(self, source, destination):
        app = App.__new__(App)
        app.root = Mock()
        app.running = app.stop_requested = False
        app.cancel = threading.Event()
        app.events = queue.Queue()
        app.tabs = Mock()
        app.tabs.index.return_value = 0
        app.active_tab = 'local'
        app.tabs.select.return_value = 'local'
        app.local_source = Value(str(source))
        app.destination = Value(str(destination))
        for name in ('remote_url', 'remote_ca', 'remote_token', 'reference'):
            setattr(app, name, Value())
        app.workers = Value('1')
        app.speed_limit = Value('Sans limite')
        app.compression = Value(True)
        app.status = Value()
        app.bar = Mock()
        app.bar.__setitem__ = Mock()
        app.begin, app.stop, app.report = Mock(), Mock(), Mock()
        app.result_button = Mock()
        app.verified_destination = None
        app.input = Mock()
        app.editable = [(app.input, 'normal')]
        return app

    def finish(self, app):
        seen = []
        while True:
            event = app.events.get(timeout=10)
            seen.append(event)
            if event[0] in ('done', 'error', 'stopped'):
                break
        for event in seen:
            app.events.put(event)
        with patch('ultra.gui.messagebox.showerror') as error:
            app.poll()
        return seen[-1], error

    def test_copy_interrupt_resume_real_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            src, dst = Path(temp)/'source', Path(temp)/'destination'
            src.mkdir()
            (src/'été_日本語.bin').write_bytes(b'abcdefgh'*(1024*1024))
            (src/'vide').touch()
            (src/'dossier vide').mkdir()
            app = self.make_app(src, dst)
            original_tick = Transfer.tick
            def tick(transfer, n):
                original_tick(transfer, n)
                if transfer.completed_bytes >= 1024*1024:
                    # Simulates a user action at a reproducible copy boundary.
                    app.request_stop()
            with patch.object(Transfer, 'tick', tick):
                app.start()
                terminal, error = self.finish(app)
            self.assertEqual(terminal[0], 'stopped')
            app.result_button.configure.assert_called_with(state='disabled')
            self.assertIsNone(app.verified_destination)
            error.assert_not_called()
            self.assertFalse(app.running)
            app.begin.configure.assert_called_with(text='Reprendre')
            self.assertTrue(list((dst/'.ultratransfert-state/parts').glob('*.part')))
            app.start()
            terminal, error = self.finish(app)
            self.assertEqual(terminal[0], 'done')
            app.result_button.configure.assert_called_with(state='normal')
            self.assertEqual(app.verified_destination,str(dst))
            error.assert_not_called()
            self.assertEqual(digest(src/'été_日本語.bin'), digest(dst/'été_日本語.bin'))
            self.assertTrue((dst/'dossier vide').is_dir())
            self.assertEqual((dst/'vide').stat().st_size, 0)
            import json
            report = json.loads((dst/'.ultratransfert-state/last-result.json').read_text())
            self.assertGreater(report['resumed_bytes'], 0)

    def test_internal_cancel_does_not_hide_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            src, dst = Path(temp)/'s', Path(temp)/'d'
            src.mkdir(); dst.mkdir()
            (src/'f').write_bytes(b'abc'); (dst/'f').write_bytes(b'xyz')
            app = self.make_app(src, dst)
            app.workers.set('2')
            app.start()
            terminal, error = self.finish(app)
            self.assertEqual(terminal[0], 'error')
            app.result_button.configure.assert_called_with(state='disabled')
            self.assertTrue(app.cancel.is_set())  # Engine abort signal, not a user stop.
            error.assert_called_once()
            self.assertIn('autre destination vide', terminal[1])
            self.assertEqual((dst/'f').read_bytes(), b'xyz')

    def test_fields_frozen_and_restored(self):
        app = self.make_app('source', 'destination')
        app.set_running(True)
        app.input.configure.assert_called_with(state='disabled')
        app.set_running(False)
        app.input.configure.assert_called_with(state='normal')
        app.tabs.select.assert_called_with('local')

    def test_late_progress_preserves_stop_message(self):
        app = self.make_app('source', 'destination')
        app.running = True
        app.request_stop()
        status = app.status.get()
        app.events.put(('progress', 100, 200, 1))
        app.events.put(('phase', 'Copie et vérification des fichiers'))
        app.poll()
        self.assertEqual(app.status.get(), status)

    def test_real_error_wins_over_requested_stop(self):
        self.assertEqual(outcome(['Conflit destination : f', 'Transfert interrompu ; les fichiers partiels sont conservés.'], True), 'error')
        self.assertEqual(outcome(['Vérification interrompue ; reprise possible.'], True), 'stopped')
        self.assertEqual(outcome(['Vérification interrompue ; reprise possible.']), 'error')
        self.assertEqual(outcome([], True), 'done')

    def test_actionable_space_and_tls_errors(self):
        self.assertIn('Libérez', error_action('Espace insuffisant : 200 requis'))
        self.assertIn('TLS reste obligatoire', error_action('SSL certificate verify failed'))

    def test_open_uses_verified_destination_after_field_change(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'été 日本語';path.mkdir()
            app=self.make_app('source',path)
            app.verified_destination=str(path)
            app.destination.set('autre destination')
            finished=threading.Event()
            with patch('ultra.gui.sys.platform','win32'),patch('ultra.gui.os.startfile',create=True,side_effect=lambda _:finished.set()) as open_folder:
                app.open_destination()
                self.assertTrue(finished.wait(5))
                open_folder.assert_called_once_with(str(path.resolve()))
            finished.clear()
            with patch('ultra.gui.sys.platform','linux'),patch('ultra.gui.subprocess.run',side_effect=lambda *a,**k:finished.set()) as run:
                app.open_destination()
                self.assertTrue(finished.wait(5))
                self.assertEqual(run.call_args.args[0],['xdg-open',str(path.resolve())])

    def test_open_failure_keeps_result_and_explains_manual_action(self):
        app=self.make_app('source','destination')
        app.verified_destination='/dossier-ultratransfert-absent'
        app.status.set('Copie terminée et vérifiée')
        with patch('ultra.gui.messagebox.showerror') as error:
            app.open_destination()
            event=app.events.get(timeout=5)
            self.assertEqual(event[0],'open_error')
            app.events.put(event);app.poll()
        self.assertIn('Ouvrez manuellement',error.call_args.args[1])
        self.assertEqual(app.status.get(),'Copie terminée et vérifiée')

    def test_open_not_available_while_copying_or_without_success(self):
        app=self.make_app('source','destination')
        with patch('ultra.gui.subprocess.run') as run,patch('ultra.gui.os.startfile',create=True) as start:
            app.open_destination()
            app.verified_destination='destination';app.running=True
            app.open_destination()
        run.assert_not_called();start.assert_not_called()

    def test_open_slow_manager_does_not_block_interface(self):
        with tempfile.TemporaryDirectory() as temp:
            app=self.make_app('source',temp);app.verified_destination=temp
            entered=threading.Event();release=threading.Event();finished=threading.Event()
            def slow(*args,**kwargs):
                entered.set();release.wait(5);finished.set()
            with patch('ultra.gui.sys.platform','linux'),patch('ultra.gui.subprocess.run',side_effect=slow):
                try:
                    app.open_destination()
                    self.assertTrue(entered.wait(5))
                    self.assertFalse(finished.is_set())
                    app.events.put(('progress',1,2,1));app.poll()
                finally:
                    release.set()
                self.assertTrue(finished.wait(5))
