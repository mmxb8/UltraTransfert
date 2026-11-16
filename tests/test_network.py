import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ultra.engine import LocalSource, Options, Transfer, TransferError, digest
from ultra.network import RemoteSource, make_server


class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import shutil
        if not shutil.which("openssl"):
            raise unittest.SkipTest("openssl CLI absent ; fournir un certificat de test")
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.cert, cls.key = cls.root/"cert.pem", cls.root/"key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(cls.key), "-out", str(cls.cert), "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case = tempfile.TemporaryDirectory(dir=self.root)
        self.source = Path(self.case.name)/"source"
        self.source.mkdir()
        (self.source/"sous-dossier").mkdir()
        (self.source/"vide").mkdir()
        (self.source/"sous-dossier"/"été.bin").write_bytes(os.urandom(180000))
        (self.source/"répétitif").write_bytes(b"ABCD"*70000)
        self.token = "token-test-"+"x"*48
        self.server = make_server(LocalSource(self.source), ("127.0.0.1", 0), self.cert, self.key, self.token, "auto")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"https://localhost:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.case.cleanup()

    def test_tls_roundtrip_raw_and_compressed(self):
        for encoding in ("none", "gzip", "auto"):
            with self.subTest(encoding=encoding):
                remote = RemoteSource(self.url, self.token, self.cert, encoding)
                dest = Path(self.case.name)/encoding
                r = Transfer(remote, dest, Options(buffer_size=65536)).run()
                self.assertFalse(r.errors, r.errors)
                self.assertTrue((dest/"vide").is_dir())
                self.assertEqual(digest(dest/"sous-dossier"/"été.bin"), digest(self.source/"sous-dossier"/"été.bin"))
                self.assertEqual(digest(dest/"répétitif"), digest(self.source/"répétitif"))

    def test_wrong_token_rejected(self):
        with self.assertRaises(HTTPError) as error:
            RemoteSource(self.url, "wrong", self.cert)
        self.assertEqual(error.exception.code, 401)

    def test_untrusted_certificate_rejected(self):
        with self.assertRaises(URLError):
            RemoteSource(self.url, self.token, None)

    def test_hostname_verification(self):
        with self.assertRaises(URLError):
            RemoteSource(self.url.replace("localhost", "127.0.0.1"), self.token, self.cert)

    def test_no_plain_http(self):
        with self.assertRaises(TransferError):
            RemoteSource("http://localhost", self.token, self.cert)

    def test_path_traversal_not_exposed(self):
        ctx = ssl.create_default_context(cafile=str(self.cert))
        for path in ("/file?id=-1", "/file?id=../../etc/passwd", "/../../etc/passwd"):
            request = Request(self.url+path, headers={"Authorization": "Bearer "+self.token})
            with self.assertRaises(HTTPError) as error:
                urlopen(request, context=ctx)
            self.assertIn(error.exception.code, (400, 404))

    def test_remote_resume(self):
        remote = RemoteSource(self.url, self.token, self.cert, "gzip")
        dest = Path(self.case.name)/"resumed"
        event = threading.Event()
        def progress(n, total):
            if n >= 65536:
                event.set()
        r = Transfer(remote, dest, Options(workers=1, buffer_size=65536), progress, event).run()
        self.assertTrue(r.errors)
        r = Transfer(remote, dest, Options(buffer_size=65536)).run()
        self.assertFalse(r.errors, r.errors)
        self.assertGreater(r.resumed_bytes, 0)

    def test_auto_compression_selects_by_content(self):
        remote = RemoteSource(self.url, self.token, self.cert, "auto")
        for entry in remote.entries:
            if entry.kind != "file":
                continue
            with remote.request(f"/file?id={remote.index[entry.path]}") as response:
                if entry.path == "répétitif":
                    self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
                else:
                    self.assertIsNone(response.headers.get("Content-Encoding"))
                response.read()

    def test_experimental_client_requires_explicit_server_support(self):
        remote = RemoteSource(self.url, self.token, self.cert, "ultra")
        entry = next(e for e in remote.entries if e.kind == 'file')
        with self.assertRaisesRegex(TransferError, 'non négociée'):
            remote.open(entry)


if __name__ == "__main__":
    unittest.main()
