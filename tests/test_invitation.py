"""Invitation : parsing borné, confiance explicite et HTTPS réel en boucle locale."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from ultra.engine import LocalSource, Transfer, Options, TransferError, digest
from ultra.invitation import write_invitation, read_invitation, parse_invitation, LIMIT
from ultra.network import make_server
from ultra.gui import App
import test_ui_workflow as workflow


class InvitationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('openssl'):
            raise unittest.SkipTest('openssl CLI absent')
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for prefix in ('server', 'other'):
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', str(cls.root/(prefix+'.key')), '-out', str(cls.root/(prefix+'.pem')),
                '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.token = 'secret-test-'+('T'*48)
        cls.tokenfile = cls.root/'token.txt'
        cls.tokenfile.write_text(cls.token)
        cls.cert, cls.key = cls.root/'server.pem', cls.root/'server.key'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def make_data(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            path = Path(temp)/'accès.utconnect'
            invitation = write_invitation('https://localhost:8443', self.cert, self.tokenfile, path)
            return json.loads(path.read_text()), invitation

    @contextmanager
    def share(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            root = Path(temp); src = root/'source'; src.mkdir()
            (src/'été_日本語.bin').write_bytes(bytes(range(256))*8192)
            (src/'.caché').write_bytes(b'hidden')
            (src/'vide').touch(); (src/'dossier vide').mkdir()
            server = make_server(LocalSource(src), ('127.0.0.1', 0), self.cert, self.key, self.token, 'auto')
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                path = root/'invitation.utconnect'
                profile = write_invitation(f'https://localhost:{server.server_port}', self.cert, self.tokenfile, path)
                yield root, src, path, profile, server
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=5)

    def test_export_is_private_no_key_no_overwrite_no_network(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            output = Path(temp)/'invitation.utconnect'
            with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
                profile = write_invitation('https://localhost:8443', self.cert, self.tokenfile, output)
            self.assertNotIn('PRIVATE KEY', output.read_text())
            self.assertNotIn(self.token, repr(profile))
            if os.name != 'nt':
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                write_invitation(profile.url, self.cert, self.tokenfile, output)
            self.assertEqual(output.read_bytes(), before)
            self.assertFalse(list(Path(temp).glob('.invitation-*')))

    def test_parser_rejects_invalid_fields_and_origins(self):
        data, unused = self.make_data()
        for url in ['http://localhost', 'https://user:pass@localhost', 'https://localhost/path',
                    'https://localhost?token=x', 'https://localhost#x', 'https:///missing',
                    'https://localhost:99999', 'https://local\nhost', 'https://local\\host']:
            with self.subTest(url=url), self.assertRaises(TransferError):
                parse_invitation(json.dumps({**data, 'url': url}).encode())
        for patch_data in [{'token': 'short'}, {'token': self.token+'\r\n'},
                           {'token': 123}, {'format': 'unknown'}, {'certificate_sha256': '0'*64},
                           {'certificate_pem': self.key.read_text()}]:
            with self.subTest(keys=list(patch_data)), self.assertRaises(TransferError):
                parse_invitation(json.dumps({**data, **patch_data}).encode())
        with self.assertRaises(TransferError):
            parse_invitation(json.dumps({**data, 'unknown': 1}).encode())

    def test_limits_duplicates_and_invalid_json(self):
        for raw in [b'x'*(LIMIT+1), b'\xff', b'[]', b'{"format":1,"format":2}', b'['*2000+b']'*2000]:
            with self.subTest(length=len(raw)), self.assertRaises(TransferError):
                parse_invitation(raw)

    def test_tls_invitation_copy_interrupt_resume(self):
        with self.share() as (root, src, path, profile, server):
            # No certificate/token files needed on the receiving side after import.
            imported = read_invitation(path)
            path.unlink()
            remote = imported.remote_source()
            self.assertTrue(remote.context.check_hostname)
            self.assertEqual(remote.context.verify_mode, ssl.CERT_REQUIRED)
            cancel = threading.Event()
            def progress(n, total):
                if n >= 65536: cancel.set()
            dst = root/'destination'
            result = Transfer(remote, dst, Options(workers=1, buffer_size=65536), progress, cancel).run()
            self.assertTrue(result.errors)
            result = Transfer(imported.remote_source(), dst, Options(workers=1, buffer_size=65536)).run()
            self.assertFalse(result.errors, result.errors)
            self.assertGreater(result.resumed_bytes, 0)
            self.assertEqual(digest(src/'été_日本語.bin'), digest(dst/'été_日本語.bin'))
            self.assertTrue((dst/'dossier vide').is_dir())
            self.assertEqual((dst/'vide').stat().st_size, 0)

    def test_hostname_certificate_and_token_still_required(self):
        with self.share() as (root, src, path, profile, server):
            data = json.loads(path.read_text())
            variants = [{**data, 'url': profile.url.replace('localhost', '127.0.0.1')},
                        {**data, 'token': 'Z'*48}]
            other_pem = (self.root/'other.pem').read_text()
            from ultra.invitation import certificate_fingerprint
            variants.append({**data, 'certificate_pem': other_pem,
                             'certificate_sha256': certificate_fingerprint(other_pem)})
            for variant in variants:
                with self.subTest(changed=[k for k in variant if variant[k]!=data[k]]), self.assertRaises((URLError, HTTPError)):
                    parse_invitation(json.dumps(variant).encode()).remote_source()

    def test_redirect_is_not_followed(self):
        with self.share() as (root, src, path, profile, server):
            remote = profile.remote_source()
            calls = []
            def redirect(handler):
                calls.append(handler.path)
                handler.send_response(302)
                handler.send_header('Location', profile.url+'/stolen')
                handler.end_headers()
            with patch.object(server.RequestHandlerClass, 'do_GET', redirect):
                with self.assertRaisesRegex(TransferError, 'Redirection'):
                    remote.get_manifest()
            self.assertEqual(calls, ['/manifest'])

    def test_gui_confirmation_precedes_connection_and_can_be_refused(self):
        with self.share() as (root, src, path, profile, server):
            app = workflow.WorkflowTests().make_app(src, root/'destination')
            app.invitation = None
            app.manual = Mock(); app.invitation_status = workflow.Value()
            with patch('ultra.gui.filedialog.askopenfilename', return_value=str(path)), \
                 patch('ultra.gui.messagebox.askyesno', return_value=False), \
                 patch('socket.socket', side_effect=AssertionError('No network before start')):
                app.open_invitation()
            self.assertIsNone(app.invitation)
            with patch('ultra.gui.filedialog.askopenfilename', return_value=str(path)), \
                 patch('ultra.gui.messagebox.askyesno', return_value=True) as confirm:
                app.open_invitation()
            self.assertNotIn(self.token, confirm.call_args.args[1])
            self.assertEqual(app.invitation.url, profile.url)
            app.tabs.index.return_value = 1
            app.start()
            terminal, error = workflow.WorkflowTests().finish(app)
            self.assertEqual(terminal[0], 'done')
            error.assert_not_called()
            self.assertEqual(digest(src/'été_日本語.bin'), digest(root/'destination/été_日本語.bin'))

    def test_cli_export_prints_no_secret(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            output = Path(temp)/'cli.utconnect'
            result = subprocess.run([os.sys.executable, '-m', 'ultra', 'invite', 'https://localhost:8443',
                str(output), '--cert', str(self.cert), '--token-file', str(self.tokenfile)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            self.assertNotIn(self.token, result.stdout+result.stderr)
