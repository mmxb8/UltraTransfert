"""Partage géré : TLS réel en boucle locale ; contrôleur graphique sans écran."""
from contextlib import contextmanager
from pathlib import Path
import os
import queue
import socket
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from ultra.engine import LocalSource, Transfer, Options, TransferError, digest
from ultra.invitation import write_invitation, read_invitation
from ultra.network import make_server
from ultra.share_setup import prepare_share, PreparedShare
from ultra.share_session import ShareSession
from ultra.share_setup_gui import SetupDialog
import test_ui_workflow as workflow


class ShareSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: import cryptography
        except ImportError: raise unittest.SkipTest('Complément sharing absent')
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.base=prepare_share('https://localhost:8443',cls.root/'private')
        cls.profile=read_invitation(cls.base.invitation_path)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    @contextmanager
    def case(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            root=Path(temp);src=root/'source';src.mkdir()
            (src/'été_日本語.bin').write_bytes(os.urandom(300000))
            (src/'vide').touch();(src/'dossier vide').mkdir()
            with socket.socket() as reserve:
                reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
            url=f'https://localhost:{port}'
            path=root/'invite.utconnect'
            write_invitation(url,self.base.directory/'server-cert.pem',self.base.directory/'token.txt',path)
            prepared=PreparedShare(self.base.directory,path,url,self.base.certificate_sha256)
            session=ShareSession()
            try:yield root,src,prepared,session,port
            finally:session.stop()

    def test_constructor_no_listener(self):
        with patch('socket.socket',side_effect=AssertionError('No network')):
            self.assertFalse(ShareSession().active)

    def test_tls_scope_and_stop_restart(self):
        with self.case() as (root,src,prepared,session,port):
            session.start(src,prepared)
            self.assertEqual(session._server.server_address[0],'127.0.0.1')
            profile=read_invitation(prepared.invitation_path)
            result=Transfer(profile.remote_source(),root/'dest').run()
            self.assertFalse(result.errors,result.errors)
            self.assertEqual(digest(src/'été_日本語.bin'),digest(root/'dest/été_日本語.bin'))
            self.assertTrue((root/'dest/dossier vide').is_dir())
            with self.assertRaisesRegex(TransferError,'déjà ouvert'):session.start(src,prepared)
            session.stop();self.assertFalse(session.active)
            with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=.3)
            session.start(src,prepared)
            result=Transfer(profile.remote_source(),root/'dest').run()
            self.assertFalse(result.errors,result.errors)
            self.assertEqual(result.copied,0)

    def test_idle_tls_connection_does_not_block_stop(self):
        with self.case() as (root,src,prepared,session,port):
            session.start(src,prepared)
            server=session._server
            with socket.create_connection(('127.0.0.1',port),timeout=2) as idle:
                deadline=time.monotonic()+2
                while not server._connections and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(server._connections)
                started=time.monotonic();session.stop()
                self.assertLess(time.monotonic()-started,2)
                try:remaining=idle.recv(1)
                except ConnectionResetError:remaining=b''
                self.assertEqual(remaining,b'')

    def test_stop_mid_transfer_and_verified_resume(self):
        with self.case() as (root,src,prepared,session,port):
            block=os.urandom(1024*1024)
            with (src/'big.bin').open('wb') as stream:
                for unused in range(64):stream.write(block)
            session.start(src,prepared)
            profile=read_invitation(prepared.invitation_path)
            stopped=[False]
            def progress(n,total):
                if n>=65536 and not stopped[0]:
                    stopped[0]=True;session.stop()
            result=Transfer(profile.remote_source(),root/'dest',Options(workers=1,buffer_size=65536),progress).run()
            self.assertTrue(result.errors)
            self.assertFalse((root/'dest/big.bin').exists())
            self.assertFalse(session.active)
            session.start(src,prepared)
            result=Transfer(profile.remote_source(),root/'dest',Options(workers=1,buffer_size=65536)).run()
            self.assertFalse(result.errors,result.errors)
            self.assertGreater(result.resumed_bytes,0)
            self.assertEqual(digest(src/'big.bin'),digest(root/'dest/big.bin'))

    def test_invalid_certificate_never_binds(self):
        with self.case() as (root,src,prepared,session,port):
            with patch('socket.socket',side_effect=AssertionError('Must not bind')), self.assertRaises(OSError):
                make_server(LocalSource(src),('127.0.0.1',port),self.base.directory/'server-cert.pem',root/'missing-key',self.profile.token)
            self.assertFalse(session.active)

    def test_profile_secret_mismatch_rejected_without_listener(self):
        with self.case() as (root,src,prepared,session,port):
            fake=root/'fake-token';fake.write_text('not-the-original-'+'z'*48)
            prepared.invitation_path.unlink()
            write_invitation(prepared.url,self.base.directory/'server-cert.pem',fake,prepared.invitation_path)
            with patch('socket.socket',side_effect=AssertionError('Must not bind')), self.assertRaisesRegex(TransferError,'différent'):
                session.start(src,prepared)
            self.assertFalse(session.active)

    def test_wildcard_bind_rejected(self):
        with self.case() as (root,src,prepared,session,port):
            url=f'https://0.0.0.0:{port}'
            path=root/'wildcard.utconnect'
            write_invitation(url,self.base.directory/'server-cert.pem',self.base.directory/'token.txt',path)
            bad=PreparedShare(self.base.directory,path,url,self.base.certificate_sha256)
            with patch('socket.socket',side_effect=AssertionError('Must not bind')), self.assertRaises(TransferError):session.start(src,bad)

    def test_gui_start_and_close_stops_real_listener(self):
        with self.case() as (root,src,prepared,session,port):
            dialog=SetupDialog.__new__(SetupDialog)
            dialog.window=Mock();dialog.running=False;dialog.events=queue.Queue()
            dialog.prepared=prepared;dialog.session=session;dialog._close_after_stop=False
            dialog.url=workflow.Value(prepared.url);dialog.source=workflow.Value(str(src))
            for name in ('address','prepare_button','load_button','source_entry','source_button','start_button','stop_button','show'):
                setattr(dialog,name,Mock())
            dialog.start_share()
            event=dialog.events.get(timeout=10);self.assertEqual(event[0],'sharing')
            dialog.events.put(event);dialog.poll()
            self.assertTrue(session.active)
            dialog.source_entry.configure.assert_called_with(state='disabled')
            self.assertIn(str(src),dialog.show.call_args.args[0])
            self.assertNotIn(self.profile.token,dialog.show.call_args.args[0])
            result=Transfer(read_invitation(prepared.invitation_path).remote_source(),root/'dest').run()
            self.assertFalse(result.errors,result.errors)
            dialog.close()
            event=dialog.events.get(timeout=10);self.assertEqual(event[0],'stopped')
            dialog.events.put(event);dialog.poll()
            dialog.window.destroy.assert_called_once()
            self.assertFalse(session.active)
            with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=.3)

    def test_changed_address_never_uses_previous_preparation(self):
        with self.case() as (root,src,prepared,session,port):
            dialog=SetupDialog.__new__(SetupDialog)
            dialog.window=Mock();dialog.running=False;dialog.session=Mock(active=False)
            dialog.prepared=prepared;dialog.url=workflow.Value('https://127.0.0.1:8443')
            dialog.source=workflow.Value(str(src))
            with patch('ultra.share_setup_gui.messagebox.showerror') as error:dialog.start_share()
            error.assert_called_once();dialog.session.start.assert_not_called()
