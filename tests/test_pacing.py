import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from ultra.engine import LocalSource,Options,Transfer,TransferError,digest
from ultra.pacing import BytePacer
import test_ui_workflow as workflow


class PacingTests(unittest.TestCase):
    def test_reservations_use_aggregate_time_not_per_file(self):
        clock=[0.0]
        class ClockEvent:
            def is_set(self):return False
            def wait(self,delay):clock[0]+=delay;return False
        pacer=BytePacer(100,clock=lambda:clock[0])
        event=ClockEvent()
        for size in (100,50,0,250):self.assertFalse(pacer.wait(size,event))
        self.assertAlmostEqual(clock[0],4.0)
        clock[0]=20;self.assertFalse(pacer.wait(100,event));self.assertEqual(clock[0],21)

    def test_wait_does_not_hold_shared_lock_and_is_cancellable(self):
        entered=threading.Event();stop=threading.Event();pacer=BytePacer(.001)
        class Event:
            def is_set(self):return stop.is_set()
            def wait(self,delay):entered.set();return stop.wait(delay)
        result=[];thread=threading.Thread(target=lambda:result.append(pacer.wait(100,Event())))
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            self.assertTrue(pacer.lock.acquire(timeout=1));pacer.lock.release()
        finally:stop.set();thread.join(timeout=3)
        self.assertFalse(thread.is_alive());self.assertEqual(result,[True])

    def test_invalid_values_and_native_combination(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir()
            for value in (-1,float('nan'),float('inf'),True,'1'):
                with self.subTest(value=value),self.assertRaises(TransferError):Transfer(LocalSource(src),Path(tmp)/'dest',Options(max_bytes_per_second=value))
            with self.assertRaisesRegex(TransferError,'moteur Python'):Transfer(LocalSource(src),Path(tmp)/'dest',Options(native='helper',max_bytes_per_second=1e6))

    def test_cancellation_in_pacing_preserves_partial_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir();dst=Path(tmp)/'dst'
            data=bytes(range(256))*4096;(src/'été_日本語').write_bytes(data)
            event=threading.Event();entered=threading.Event();real=BytePacer.wait
            calls=[0]
            def wait(pacer,count,cancel):
                calls[0]+=1
                if calls[0]==2:entered.set()
                return real(pacer,count,cancel)
            transfer=Transfer(LocalSource(src),dst,Options(workers=1,buffer_size=65536,max_bytes_per_second=1e6),cancel=event)
            results=[]
            with patch.object(BytePacer,'wait',wait):
                thread=threading.Thread(target=lambda:results.append(transfer.run()));thread.start()
                try:self.assertTrue(entered.wait(5))
                finally:event.set();thread.join(timeout=5)
            self.assertFalse(thread.is_alive());self.assertTrue(results[0].errors)
            self.assertFalse((dst/'été_日本語').exists())
            result=Transfer(LocalSource(src),dst,Options(max_bytes_per_second=100e6)).run()
            self.assertFalse(result.errors,result.errors);self.assertGreaterEqual(result.resumed_bytes,65536)
            self.assertEqual((dst/'été_日本語').read_bytes(),data)

    def test_existing_file_source_hash_is_paced(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir();dst=Path(tmp)/'dst';dst.mkdir()
            data=b'x'*99003;(src/'f').write_bytes(data);(dst/'f').write_bytes(data)
            transfer=Transfer(LocalSource(src),dst,Options(max_bytes_per_second=100e6))
            paced=[]
            with patch.object(transfer.pacer,'wait',side_effect=lambda n,c:paced.append(n) or False):result=transfer.run()
            self.assertFalse(result.errors);self.assertEqual(sum(paced),len(data))

    def test_gui_snapshots_limit_for_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir();(src/'f').write_bytes(b'abc')
            app=workflow.WorkflowTests().make_app(src,Path(tmp)/'dst');app.speed_limit.set('5')
            seen=[];real=Transfer
            def create(*args,**kw):seen.append(args[2].max_bytes_per_second);return real(*args,**kw)
            with patch('ultra.gui.Transfer',side_effect=create):
                app.start();terminal,error=workflow.WorkflowTests().finish(app)
            self.assertEqual(terminal[0],'done');self.assertEqual(seen,[5e6])

    def test_cli_limit_option_copies_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'src';src.mkdir();dst=Path(tmp)/'dst';(src/'f').write_bytes(b'abc'*1000)
            proc=subprocess.run([sys.executable,'-m','ultra','copy',str(src),str(dst),'--limit-mb-s','10'],capture_output=True,text=True,timeout=10)
            self.assertEqual(proc.returncode,0,proc.stderr);self.assertFalse(json.loads(proc.stdout)['errors'])
            self.assertEqual(json.loads(proc.stdout)['max_bytes_per_second'],10e6)
            self.assertEqual(digest(src/'f'),digest(dst/'f'))
