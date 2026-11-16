"""Annulation réelle de préparation, GUI doublée et TLS local après redémarrage."""
from contextlib import contextmanager
from pathlib import Path
import queue
import socket
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from ultra.engine import LocalSource, OperationCancelled, Transfer, digest, inventory
from ultra.invitation import write_invitation, read_invitation
from ultra.network import make_server, TransferHTTPServer
from ultra.share_setup import prepare_share, PreparedShare
from ultra.share_session import ShareSession
from ultra.share_setup_gui import SetupDialog
from test_ui_workflow import Value
from ultra.gui import App


class PrepareCancelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.base=prepare_share('https://localhost:8443',cls.root/'private')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    @contextmanager
    def case(self):
        with tempfile.TemporaryDirectory(dir=self.root) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir()
            (src/'été_日本語').write_bytes(b'data'*1024*1024)
            (src/'vide').touch();(src/'dossier vide').mkdir()
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            invite=root/'acces.utconnect';url=f'https://localhost:{port}'
            write_invitation(url,self.base.directory/'server-cert.pem',self.base.directory/'token.txt',invite)
            prepared=PreparedShare(self.base.directory,invite,url,self.base.certificate_sha256)
            obj=SetupDialog.__new__(SetupDialog)
            obj.window=Mock();obj.running=False;obj.events=queue.Queue();obj.prepared=prepared
            obj.session=ShareSession();obj._close_after_stop=False;obj._poll_id='timer'
            obj.url=Value(url);obj.source=Value(str(src))
            for n in ('address','prepare_button','load_button','source_entry','source_button','start_button','stop_button','show'):setattr(obj,n,Mock())
            try:yield root,src,obj,port
            finally:obj.session.stop()

    def terminal(self,obj):
        event=obj.events.get(timeout=10);obj.events.put(event)
        with patch('ultra.share_setup_gui.messagebox.showerror') as error:obj.poll()
        return event,error

    def test_pre_cancel_no_inventory_or_listener(self):
        cancel=threading.Event();cancel.set()
        with patch('os.scandir',side_effect=AssertionError('Pas de scan')),self.assertRaises(OperationCancelled):inventory(self.root,cancel=cancel)
        with self.case() as (_,src,obj,port):
            with patch('socket.socket',side_effect=AssertionError('Pas de socket')),self.assertRaises(OperationCancelled):obj.session.start(src,obj.prepared,cancel=cancel)
            self.assertFalse(obj.session.active)

    def test_inventory_cancel_during_walk(self):
        with self.case() as (_,src,obj,port):
            cancel=threading.Event()
            import ultra.engine as engine
            real=engine.is_link
            calls=[0]
            def checked(s):
                calls[0]+=1
                if calls[0]>=2:cancel.set()
                return real(s)
            with patch('ultra.engine.is_link',side_effect=checked),self.assertRaises(OperationCancelled):inventory(src,cancel=cancel)

    def test_cancel_digest_and_restart_tls(self):
        self.run_gui_cancel(close=False)

    def test_close_during_prepare_waits_for_confirmation(self):
        self.run_gui_cancel(close=True)

    def run_gui_cancel(self,close):
        with self.case() as (root,src,obj,port):
            expected=digest(src/'été_日本語');entered=threading.Event();release=threading.Event()
            def gated(*a,**kw):
                entered.set()
                if not release.wait(5):raise RuntimeError('test gate timeout')
                return digest(*a,**kw)
            with patch('ultra.network.digest',side_effect=gated):
                try:
                    obj.start_share();self.assertTrue(entered.wait(5))
                    obj.stop_button.configure.assert_called_with(text='Annuler la préparation',state='normal')
                    obj.close() if close else obj.stop_share()
                    obj.window.destroy.assert_not_called()
                finally:release.set()
                event,error=self.terminal(obj)
            self.assertEqual(event[0],'cancelled');error.assert_not_called()
            self.assertFalse(obj.session.active);self.assertEqual(digest(src/'été_日本語'),expected)
            with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=.2)
            if close:obj.window.destroy.assert_called_once()
            else:
                obj.start_share();event,error=self.terminal(obj);self.assertEqual(event[0],'sharing')
                result=Transfer(read_invitation(obj.prepared.invitation_path).remote_source(),root/'dest').run()
                self.assertFalse(result.errors,result.errors)
                self.assertEqual(digest(root/'dest/été_日本語'),expected)

    def test_cancel_delta_hash_before_bind(self):
        with self.case() as (_,src,obj,port):
            source=LocalSource(src);cancel=threading.Event();real=source.open
            def opening(*a,**kw):cancel.set();return real(*a,**kw)
            profile=read_invitation(obj.prepared.invitation_path)
            with patch.object(source,'open',side_effect=opening),patch('socket.socket',side_effect=AssertionError('Pas de socket')),self.assertRaises(OperationCancelled):
                make_server(source,('127.0.0.1',port),self.base.directory/'server-cert.pem',self.base.directory/'server-key.pem',profile.token,block_size=65536,cancel=cancel)

    def test_cancel_just_after_bind_closes_socket(self):
        with self.case() as (_,src,obj,port):
            cancel=threading.Event();profile=read_invitation(obj.prepared.invitation_path)
            def binding(*a,**kw):
                server=TransferHTTPServer(*a,**kw);cancel.set();return server
            with patch('ultra.network.TransferHTTPServer',side_effect=binding),self.assertRaises(OperationCancelled):
                make_server(LocalSource(src),('127.0.0.1',port),self.base.directory/'server-cert.pem',self.base.directory/'server-key.pem',profile.token,cancel=cancel)
            with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=.2)

    def test_cancel_after_ready_event_stops_without_ready_announcement(self):
        with self.case() as (_,src,obj,port):
            obj.start_share();event=obj.events.get(timeout=10);self.assertEqual(event[0],'sharing')
            obj.stop_share();obj.events.put(event);obj.poll()
            event,error=self.terminal(obj);self.assertEqual(event[0],'stopped')
            self.assertFalse(obj.session.active)
            self.assertFalse(any('PARTAGE OUVERT' in c.args[0] for c in obj.show.call_args_list))

    def test_other_error_not_hidden_by_cancel(self):
        with self.case() as (_,src,obj,port):
            def fail(*a,**kw):kw['cancel'].set();raise OSError('Droits refusés')
            with patch.object(obj.session,'start',side_effect=fail):
                obj.start_share();event,error=self.terminal(obj)
            self.assertEqual(event[0],'error');error.assert_called_once()

    def test_main_window_close_requests_preparation_cancel(self):
        with self.case() as (_,src,obj,port):
            obj.running=True;obj._starting=True;obj._start_cancel=threading.Event()
            app=App.__new__(App);app.setup_window=obj;app.root=Mock();app.status=Value()
            app.close()
            self.assertTrue(obj._start_cancel.is_set());app.root.destroy.assert_not_called()
            self.assertIn('Attendez le résultat',app.status.get())
