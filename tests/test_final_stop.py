"""Arrêt des inventaires finaux : moteur réel, contrôleur sans écran."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import ultra.engine as engine
from ultra.network import RemoteSource
from ultra.delta import DeltaSource
from ultra.ui_feedback import outcome
import test_ui_workflow as workflow


class FinalStopTests(unittest.TestCase):
    def test_gui_stop_at_final_inventory_empty_source_never_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source';src.mkdir();dst=Path(tmp)/'dest'
            helper=workflow.WorkflowTests();app=helper.make_app(src,dst)
            real=engine.inventory
            def inventory(path, **kw):
                # Le premier inventaire destination précède la copie, le second est final.
                if Path(path)==dst:
                    inventory.calls+=1
                    if inventory.calls==2:app.request_stop()
                return real(path,**kw)
            inventory.calls=0
            with patch.object(engine,'inventory',inventory):
                app.start();terminal,error=helper.finish(app)
            self.assertEqual(terminal[0],'stopped');error.assert_not_called()
            self.assertIsNone(app.verified_destination)
            self.assertFalse((dst/engine.STATE/'lock').exists())
            app.start();terminal,error=helper.finish(app)
            self.assertEqual(terminal[0],'done');error.assert_not_called()

    def test_stop_within_final_inventory_then_full_verified_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source';src.mkdir();dst=Path(tmp)/'dest'
            for i in range(60):(src/f'été_日本語_{i}').write_bytes(bytes([i])*8192)
            (src/'.caché').touch();(src/'dossier vide').mkdir()
            cancel=threading.Event();source=engine.LocalSource(src)
            real=engine.check_cancel;state={'final':False,'calls':0}
            def phase(text):state['final']=text.startswith('Vérification finale')
            def checkpoint(event):
                if state['final']:
                    state['calls']+=1
                    if state['calls']==10:cancel.set()
                real(event)
            with patch.object(engine,'check_cancel',checkpoint):
                result=engine.Transfer(source,dst,engine.Options(workers=1),cancel=cancel,phase=phase).run()
            self.assertEqual(outcome(result.errors,True),'stopped')
            self.assertEqual(state['calls'],10)
            self.assertFalse((dst/engine.STATE/'lock').exists())
            resumed=engine.Transfer(engine.LocalSource(src),dst).run()
            self.assertFalse(resumed.errors);self.assertEqual(resumed.reused,61)
            for p in src.iterdir():
                if p.is_file():self.assertEqual(engine.digest(p),engine.digest(dst/p.name))
            self.assertTrue((dst/'dossier vide').is_dir())

    def test_source_rechecks_receive_cancellation_before_and_after_final_verify(self):
        for stop_call in (1,2):
            with self.subTest(stop_call=stop_call),tempfile.TemporaryDirectory() as tmp:
                src=Path(tmp)/'src';src.mkdir();(src/'vide').touch()
                source=engine.LocalSource(src);cancel=threading.Event();real=source.check_all;calls=[]
                def check(cancel=None):
                    calls.append(cancel)
                    if len(calls)==stop_call:cancel.set()
                    real(cancel=cancel)
                with patch.object(source,'check_all',check):
                    result=engine.Transfer(source,Path(tmp)/'dst',cancel=cancel).run()
                self.assertEqual(outcome(result.errors,True),'stopped')
                self.assertTrue(all(c is cancel for c in calls))

    def test_real_error_during_inventory_is_not_hidden_by_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir();source=engine.LocalSource(src);cancel=threading.Event()
            def denied(*a,**kw):cancel.set();raise PermissionError('Permission denied simulée')
            with patch.object(engine,'inventory',denied):result=engine.Transfer(source,Path(tmp)/'dst',cancel=cancel).run()
            self.assertEqual(outcome(result.errors,True),'error')
            self.assertIn('Permission denied',result.errors[0])

    def test_remote_recheck_checks_before_and_after_request(self):
        remote=RemoteSource.__new__(RemoteSource);remote.payload={'entries':[]}
        event=threading.Event();event.set();remote.get_manifest=Mock(return_value=remote.payload)
        with self.assertRaises(engine.OperationCancelled):remote.check_all(cancel=event)
        remote.get_manifest.assert_not_called()
        event.clear()
        def get():event.set();return remote.payload
        remote.get_manifest=Mock(side_effect=get)
        with self.assertRaises(engine.OperationCancelled):remote.check_all(cancel=event)
        event.clear()
        def changed():event.set();return {'entries':['changed']}
        remote.get_manifest=Mock(side_effect=changed)
        with self.assertRaisesRegex(engine.TransferError,'a changé'):remote.check_all(cancel=event)

    def test_delta_forwards_recheck_cancellation(self):
        source=DeltaSource.__new__(DeltaSource);source.remote=Mock();event=threading.Event()
        source.check_all(cancel=event);source.remote.check_all.assert_called_once_with(cancel=event)

    def test_stop_after_last_directory_metadata_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir();(src/'vide').mkdir();dst=Path(tmp)/'dst'
            cancel=threading.Event();real=engine.os.utime
            def utime(path, **kw):
                real(path, **kw)
                if Path(path)==dst/'vide':cancel.set()
            with patch.object(engine.os,'utime',utime):
                result=engine.Transfer(engine.LocalSource(src),dst,cancel=cancel).run()
            self.assertEqual(outcome(result.errors,True),'stopped')
            self.assertFalse((dst/engine.STATE/'lock').exists())
            result=engine.Transfer(engine.LocalSource(src),dst).run()
            self.assertFalse(result.errors)
            self.assertEqual((src/'vide').stat().st_mtime_ns,(dst/'vide').stat().st_mtime_ns)
