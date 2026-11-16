"""Rechargement hors réseau et reprise après un nouveau contrôleur d'émission."""
import builtins
from datetime import datetime,timedelta,timezone
import hashlib
import os
from pathlib import Path
import queue
import shutil
import socket
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch

from ultra.engine import LocalSource,Transfer,Options,TransferError
from ultra.invitation import read_invitation,write_invitation
from ultra.share_setup import prepare_share
from ultra.share_restore import load_prepared_share
from ultra.share_session import ShareSession
from ultra.share_setup_gui import SetupDialog
import test_ui_workflow as workflow


class ShareRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:import cryptography
        except ImportError:raise unittest.SkipTest('Complément sharing absent pour les fixtures')
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.original=prepare_share('https://localhost:8443',cls.root/'original')
        cls.other=prepare_share('https://localhost:8443',cls.root/'other')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.case=tempfile.TemporaryDirectory(dir=self.root)
        self.folder=Path(self.case.name)/'connexion été'
        shutil.copytree(self.original.directory,self.folder)

    def tearDown(self):self.case.cleanup()

    def export(self,url='https://localhost:8443'):
        path=self.folder/'acces.utconnect';path.unlink()
        write_invitation(url,self.folder/'server-cert.pem',self.folder/'token.txt',path)

    def resign(self,start,stop):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes,serialization
        cert=x509.load_pem_x509_certificate((self.folder/'server-cert.pem').read_bytes())
        key=serialization.load_pem_private_key((self.folder/'server-key.pem').read_bytes(),password=None)
        builder=(x509.CertificateBuilder().subject_name(cert.subject).issuer_name(cert.issuer)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(start).not_valid_after(stop))
        for ext in cert.extensions:builder=builder.add_extension(ext.value,ext.critical)
        (self.folder/'server-cert.pem').write_bytes(builder.sign(key,hashes.SHA256()).public_bytes(serialization.Encoding.PEM))
        self.export()

    def dialog(self):
        obj=SetupDialog.__new__(SetupDialog)
        obj.window=Mock();obj.running=False;obj.events=queue.Queue();obj.prepared=None
        obj.session=ShareSession();obj._close_after_stop=False
        obj.url=workflow.Value('https://old-address:8443');obj.source=workflow.Value()
        for name in ('address','prepare_button','load_button','source_entry','source_button','start_button','stop_button','show'):setattr(obj,name,Mock())
        return obj

    def finish(self,obj):
        event=obj.events.get(timeout=15);obj.events.put(event)
        with patch('ultra.share_setup_gui.messagebox.showerror'):obj.poll()
        return event

    def test_restore_no_socket_no_crypto_import_and_no_rewrite(self):
        before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.folder.iterdir()}
        original_import=builtins.__import__
        def importer(name,*args,**kwargs):
            if name.startswith('cryptography'):raise ImportError('Optional dependency unavailable')
            return original_import(name,*args,**kwargs)
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('builtins.__import__',side_effect=importer):
            selected=load_prepared_share(self.folder)
        self.assertEqual(selected.url,'https://localhost:8443')
        self.assertEqual(selected.certificate_sha256,self.original.certificate_sha256)
        self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.folder.iterdir()})

    def test_token_mismatch_refused(self):
        (self.folder/'token.txt').write_text('z'*64)
        with self.assertRaisesRegex(TransferError,'différent'):load_prepared_share(self.folder)

    def test_private_key_mismatch_refused(self):
        (self.folder/'server-key.pem').write_bytes((self.other.directory/'server-key.pem').read_bytes())
        with self.assertRaisesRegex(TransferError,'TLS'):load_prepared_share(self.folder)

    def test_encrypted_key_never_prompts(self):
        from cryptography.hazmat.primitives import serialization
        key=serialization.load_pem_private_key((self.folder/'server-key.pem').read_bytes(),password=None)
        (self.folder/'server-key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.BestAvailableEncryption(b'fixture-password')))
        with patch('ultra.share_restore._verify_tls',side_effect=AssertionError('Encrypted key must be refused before decryption')),self.assertRaisesRegex(TransferError,'TLS'):load_prepared_share(self.folder)
        # The listening factory must also refuse encryption without prompting.
        from ultra.network import make_server
        import ssl
        source=Path(self.case.name)/'data';source.mkdir()
        with patch('socket.socket',side_effect=AssertionError('No listener')),self.assertRaises(ssl.SSLError):
            make_server(LocalSource(source),('127.0.0.1',0),self.folder/'server-cert.pem',self.folder/'server-key.pem','x'*64)

    def test_expired_and_future_certificates_refused_before_listen(self):
        now=datetime.now(timezone.utc)
        for start,stop in ((now-timedelta(days=2),now-timedelta(days=1)),(now+timedelta(days=1),now+timedelta(days=2))):
            self.resign(start,stop)
            with patch('socket.socket',side_effect=AssertionError('No listener')),self.assertRaisesRegex(TransferError,'invalide ou expirée'):
                load_prepared_share(self.folder)

    def test_wrong_hostname_refused_offline(self):
        self.export('https://127.0.0.1:8443')
        with patch('socket.socket',side_effect=AssertionError('No network')),self.assertRaisesRegex(TransferError,'TLS'):
            load_prepared_share(self.folder)

    def test_missing_and_excessive_files_refused(self):
        limits={'server-key.pem':16384,'server-cert.pem':16384,'token.txt':514,'acces.utconnect':32768}
        for name,maximum in limits.items():
            path=self.folder/name;raw=path.read_bytes();path.unlink()
            with self.assertRaises(OSError):load_prepared_share(self.folder)
            path.write_bytes(b'x'*(maximum+1));path.chmod(0o600)
            with self.assertRaises(TransferError):load_prepared_share(self.folder)
            path.write_bytes(raw)

    @unittest.skipIf(os.name=='nt','Symlink privileges are not assumed on Windows')
    def test_links_refused(self):
        link=Path(self.case.name)/'linked';link.symlink_to(self.folder,target_is_directory=True)
        with self.assertRaises(TransferError):load_prepared_share(link)
        key=self.folder/'server-key.pem';key.unlink();key.symlink_to(self.original.directory/'server-key.pem')
        with self.assertRaises(TransferError):load_prepared_share(self.folder)

    @unittest.skipIf(os.name=='nt','POSIX permissions only')
    def test_broad_permissions_refused_without_chmod(self):
        self.folder.chmod(0o755)
        with self.assertRaises(TransferError):load_prepared_share(self.folder)
        self.assertEqual(self.folder.stat().st_mode&0o777,0o755)
        self.folder.chmod(0o700)
        for name in ('server-key.pem','token.txt','acces.utconnect'):
            path=self.folder/name;path.chmod(0o640)
            with self.assertRaises(TransferError):load_prepared_share(self.folder)
            self.assertEqual(path.stat().st_mode&0o777,0o640);path.chmod(0o600)

    def test_configuration_change_during_validation_refused(self):
        from ultra.share_restore import _verify_tls
        def change(*args):
            _verify_tls(*args)
            (self.folder/'token.txt').write_text('z'*64)
        with patch('ultra.share_restore._verify_tls',side_effect=change),self.assertRaisesRegex(TransferError,'changé'):
            load_prepared_share(self.folder)

    def test_gui_reload_new_session_resumes_original_destination(self):
        with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
        self.export(f'https://localhost:{port}')
        selected=load_prepared_share(self.folder)
        src=Path(self.case.name)/'source';src.mkdir()
        (src/'été_日本語').write_bytes(os.urandom(8*1024*1024));(src/'vide').touch();(src/'dossier vide').mkdir()
        dst=Path(self.case.name)/'destination'
        profile=read_invitation(selected.invitation_path)
        first=ShareSession();cancel=threading.Event()
        try:
            first.start(src,selected)
            def progress(n,total):
                if n>=65536:cancel.set()
            result=Transfer(profile.remote_source(),dst,Options(workers=1,buffer_size=65536),progress,cancel).run()
            self.assertTrue(result.errors)
        finally:first.stop()
        obj=self.dialog();obj.source.set(str(src))
        try:
            with patch('ultra.share_setup_gui.filedialog.askdirectory',return_value=str(self.folder)):
                obj.load_existing()
            self.assertEqual(self.finish(obj)[0],'loaded')
            self.assertFalse(obj.session.active)
            self.assertEqual(obj.url.get(),selected.url)
            obj.start_share();self.assertEqual(self.finish(obj)[0],'sharing')
            result=Transfer(profile.remote_source(),dst,Options(workers=1,buffer_size=65536)).run()
            self.assertFalse(result.errors,result.errors);self.assertGreater(result.resumed_bytes,0)
            self.assertEqual(hashlib.sha256((src/'été_日本語').read_bytes()).digest(),hashlib.sha256((dst/'été_日本語').read_bytes()).digest())
            self.assertTrue((dst/'dossier vide').is_dir())
            self.assertNotIn(profile.token,obj.show.call_args.args[0])
        finally:obj.session.stop()

    def test_failed_gui_reload_clears_previous_selection(self):
        obj=self.dialog();obj.prepared=load_prepared_share(self.folder)
        empty=Path(self.case.name)/'empty';empty.mkdir(mode=0o700)
        with patch('ultra.share_setup_gui.filedialog.askdirectory',return_value=str(empty)):obj.load_existing()
        self.assertEqual(self.finish(obj)[0],'error')
        self.assertIsNone(obj.prepared);self.assertFalse(obj.session.active)
        obj.start_button.configure.assert_called_with(state='disabled')

    def test_gui_cancel_preserves_current_selection(self):
        obj=self.dialog();obj.prepared=load_prepared_share(self.folder);before=obj.prepared
        with patch('ultra.share_setup_gui.filedialog.askdirectory',return_value=''):obj.load_existing()
        self.assertIs(obj.prepared,before);self.assertFalse(obj.running)

    def test_configuration_change_before_listen_is_refused(self):
        from ultra.network import make_server
        selected=load_prepared_share(self.folder)
        source=Path(self.case.name)/'data';source.mkdir()
        def mutate(*args,**kwargs):
            (self.folder/'token.txt').write_text('z'*64)
            return make_server(*args,**kwargs)
        session=ShareSession()
        with patch('ultra.share_session.make_server',side_effect=mutate),patch('socket.socket',side_effect=AssertionError('No listener')),self.assertRaisesRegex(TransferError,'changé'):
            session.start(source,selected)
        self.assertFalse(session.active)
