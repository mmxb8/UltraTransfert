"""Préparation locale et certificat généré : essais Linux, pas de preuve Windows."""
import builtins
from datetime import timedelta
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from ultra.engine import LocalSource, Options, Transfer, TransferError, digest
from ultra.invitation import read_invitation
from ultra.network import make_server
from ultra.share_setup import prepare_share, _protect_windows
from ultra.share_setup_gui import SetupDialog
import test_ui_workflow as workflow


class ShareSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography import x509
        except ImportError:
            raise unittest.SkipTest('Complément sharing absent')

    def test_offline_generation_private_and_certificate_properties(self):
        from cryptography import x509
        from cryptography.x509.oid import ExtendedKeyUsageOID
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)/'profil été'
            with patch('socket.socket', side_effect=AssertionError('No network')):
                prepared = prepare_share('https://localhost:8443', directory)
            self.assertTrue(prepared.invitation_path.is_file())
            self.assertNotIn('PRIVATE KEY', prepared.invitation_path.read_text())
            profile = read_invitation(prepared.invitation_path)
            self.assertNotIn(profile.token, repr(prepared))
            cert = x509.load_pem_x509_certificate((directory/'server-cert.pem').read_bytes())
            self.assertEqual(cert.public_key().key_size, 3072)
            self.assertFalse(cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
            self.assertIn('localhost', cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName))
            self.assertIn(ExtendedKeyUsageOID.SERVER_AUTH, cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value)
            self.assertEqual(cert.not_valid_after_utc-cert.not_valid_before_utc, timedelta(days=7, minutes=5))
            if os.name != 'nt':
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                for p in directory.iterdir(): self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_new_tokens_and_certificates_each_time(self):
        with tempfile.TemporaryDirectory() as temp:
            a = prepare_share('https://localhost:8443', Path(temp)/'a')
            b = prepare_share('https://localhost:8443', Path(temp)/'b')
            self.assertNotEqual(a.certificate_sha256, b.certificate_sha256)
            self.assertNotEqual(read_invitation(a.invitation_path).token, read_invitation(b.invitation_path).token)

    def test_existing_directory_never_modified(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)/'existing'; directory.mkdir()
            keep = directory/'keep'; keep.write_bytes(b'unchanged')
            with self.assertRaises(FileExistsError): prepare_share('https://localhost:8443', directory)
            self.assertEqual(list(directory.iterdir()), [keep])
            self.assertEqual(keep.read_bytes(), b'unchanged')

    def test_bad_addresses_refused_before_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'absent'
            for url in ('http://localhost', 'https://0.0.0.0:8443', 'https://224.0.0.1:8443', 'https://-bad.example:8443', 'https://host/path', 'https://localhost:0'):
                with self.subTest(url=url), self.assertRaises(TransferError): prepare_share(url, target)
                self.assertFalse(target.exists())

    def test_missing_crypto_creates_nothing(self):
        original = builtins.__import__
        def importer(name, *args, **kwargs):
            if name.startswith('cryptography'): raise ImportError('unavailable')
            return original(name, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)/'absent'
            with patch('builtins.__import__', side_effect=importer), self.assertRaisesRegex(TransferError, 'Composant'):
                prepare_share('https://localhost:8443', directory)
            self.assertFalse(directory.exists())

    def test_write_error_cleans_only_new_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)/'new'
            keep = Path(temp)/'keep'; keep.write_bytes(b'keep')
            with patch('ultra.share_setup._write_private', side_effect=OSError('No space left')), self.assertRaises(OSError):
                prepare_share('https://localhost:8443', directory)
            self.assertFalse(directory.exists()); self.assertEqual(keep.read_bytes(), b'keep')

    def test_windows_acl_failure_precedes_key_and_secret_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)/'new'
            with patch('ultra.share_setup.sys.platform', 'win32'), \
                 patch('ultra.share_setup._protect_windows', side_effect=OSError('denied')), \
                 patch('ultra.share_setup._write_private') as write, self.assertRaisesRegex(TransferError, 'Protection'):
                prepare_share('https://localhost:8443', directory)
            write.assert_not_called(); self.assertFalse(directory.exists())

    def test_windows_acl_command_plan_only(self):
        # Mocks only: never counted as an executed ACL test on Windows.
        user = Mock(stdout='"test","S-1-5-21-111-222-333-1001"')
        with patch.dict(os.environ, {'SystemRoot': 'C:/Windows'}), \
             patch('ultra.share_setup.subprocess.run', side_effect=[user, Mock()]) as run:
            _protect_windows(Path('fixture'))
        command = run.call_args_list[1].args[0]
        self.assertIn('/inheritancelevel:r', command)
        self.assertEqual(command[-1], '*S-1-5-21-111-222-333-1001:(OI)(CI)F')

    def test_generated_ip_certificate_tls_interrupt_resume(self):
        from urllib.parse import urlsplit
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); src = root/'data'; src.mkdir()
            (src/'été_日本語').write_bytes(bytes(range(256))*8192)
            (src/'.caché').write_bytes(b'abc'); (src/'vide').touch(); (src/'dossier vide').mkdir()
            # Pick a port by asking the actual server to bind zero, then issue a new
            # invitation for that port using the generated certificate/secret.
            prepared = prepare_share('https://127.0.0.1:8443', root/'private')
            profile = read_invitation(prepared.invitation_path)
            folder = prepared.directory
            server = make_server(LocalSource(src), ('127.0.0.1',0), folder/'server-cert.pem', folder/'server-key.pem', profile.token, 'auto')
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                from dataclasses import replace
                actual = replace(profile, url=f'https://127.0.0.1:{server.server_port}')
                cancel = threading.Event()
                def progress(n,total):
                    if n>=65536: cancel.set()
                result = Transfer(actual.remote_source(), root/'dest', Options(workers=1,buffer_size=65536), progress, cancel).run()
                self.assertTrue(result.errors)
                result = Transfer(actual.remote_source(), root/'dest', Options(workers=1,buffer_size=65536)).run()
                self.assertFalse(result.errors,result.errors); self.assertGreater(result.resumed_bytes,0)
                self.assertEqual(digest(src/'été_日本語'),digest(root/'dest/été_日本語'))
                self.assertTrue((root/'dest/dossier vide').is_dir())
                with self.assertRaises(URLError):
                    replace(actual,url=actual.url.replace('127.0.0.1','localhost')).remote_source()
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)

    def test_setup_dialog_controller_no_service(self):
        with tempfile.TemporaryDirectory() as temp:
            dialog = SetupDialog.__new__(SetupDialog)
            dialog.window = Mock();dialog.running=False;dialog.events=queue.Queue()
            dialog.url=workflow.Value('https://localhost:8443')
            dialog.address=Mock();dialog.prepare_button=Mock();dialog.load_button=Mock();dialog.show=Mock()
            dialog.prepared=None;dialog.session=Mock(active=False)
            dialog.source_entry=Mock();dialog.source_button=Mock()
            dialog.start_button=Mock();dialog.stop_button=Mock()
            with patch('ultra.share_setup_gui.filedialog.askdirectory',return_value=temp): dialog.prepare()
            kind,value=dialog.events.get(timeout=20)
            self.assertEqual(kind,'done')
            dialog.events.put((kind,value)); dialog.poll()
            self.assertFalse(dialog.running)
            displayed=dialog.show.call_args.args[0]
            self.assertIn('Aucun partage',displayed)
            self.assertNotIn(read_invitation(value.invitation_path).token,displayed)

    def test_cli_prepare_no_secret_output(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'prepared'
            proc=subprocess.run([sys.executable,'-m','ultra','prepare','https://localhost:8443',str(folder)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            token=read_invitation(folder/'acces.utconnect').token
            self.assertNotIn(token,proc.stdout+proc.stderr)
            self.assertIn('Aucun service',proc.stdout)

    def test_private_configuration_cannot_be_shared(self):
        with tempfile.TemporaryDirectory() as temp:
            prepared=prepare_share('https://localhost:8443',Path(temp)/'private')
            folder=prepared.directory
            profile=read_invitation(prepared.invitation_path)
            with patch('socket.socket',side_effect=AssertionError('No listener')), self.assertRaisesRegex(TransferError,'clé privée'):
                make_server(LocalSource(folder),('127.0.0.1',0),folder/'server-cert.pem',folder/'server-key.pem',profile.token)

    def test_frozen_smoke_branch_prepares_crypto(self):
        # Simulated frozen flag under Linux; never treated as an actual EXE test.
        from ultra.smoke import check
        with patch('ultra.smoke.sys.frozen',True,create=True):
            result=check(require_gui=False)
        self.assertTrue(result['sharing_prepared'])
        self.assertTrue(result['sharing_session_checked'])
        self.assertTrue(result['sharing_restore_checked'])
        self.assertEqual(result['status'],'passed')
