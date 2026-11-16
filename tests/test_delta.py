import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from ultra.delta import DeltaSource
from ultra.engine import LocalSource, Options, STATE, Transfer, TransferError, digest
from ultra.network import RemoteSource, make_server

BLOCK = 65536


class DeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import shutil
        if not shutil.which('openssl'):
            raise unittest.SkipTest('OpenSSL absent')
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.cert, cls.key = cls.root/'cert.pem', cls.root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.key),'-out',str(cls.cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case = tempfile.TemporaryDirectory(dir=self.root)
        self.base = Path(self.case.name)
        self.src, self.ref, self.dst = (self.base/n for n in ('source','reference','destination'))
        self.src.mkdir(); self.ref.mkdir()
        self.server = None
        self.data = os.urandom(BLOCK*10+123)
        (self.src/'large.bin').write_bytes(self.data)
        self.token = 'delta-test-'+'x'*48

    def tearDown(self):
        if self.server:
            self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=5)
        self.case.cleanup()

    def remote(self, compression='none', blocks=BLOCK):
        self.server = make_server(LocalSource(self.src), ('127.0.0.1',0), self.cert,self.key,self.token,compression,blocks)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url = f'https://localhost:{self.server.server_port}'
        return RemoteSource(self.url,self.token,self.cert,compression)

    def transfer(self, origin, cancel=None, progress=None, workers=1):
        return Transfer(origin,self.dst,Options(workers=workers,buffer_size=BLOCK),progress,cancel).run()

    def test_changed_block_and_renamed_reference(self):
        old = bytearray(self.data); old[BLOCK*3+11] ^= 1
        (self.ref/'ancien_été.bin').write_bytes(old)
        (self.src/'dossier vide').mkdir()
        (self.src/'vide').write_bytes(b'')
        origin = DeltaSource(self.remote(),self.ref)
        result = self.transfer(origin,workers=4)
        self.assertEqual(result.errors,[])
        self.assertEqual((self.dst/'large.bin').read_bytes(),self.data)
        self.assertEqual(origin.statistics()['downloaded_payload_bytes'],BLOCK)
        self.assertEqual(origin.statistics()['reused_payload_bytes'],len(self.data)-BLOCK)
        self.assertEqual((self.ref/'ancien_été.bin').read_bytes(),bytes(old))
        self.assertTrue((self.dst/'dossier vide').is_dir())
        saved = json.loads((self.dst/STATE/'last-result.json').read_text())
        self.assertEqual(saved['delta']['downloaded_blocks'],1)

    def test_first_transfer_fetches_all(self):
        origin = DeltaSource(self.remote(),self.ref)
        result = self.transfer(origin)
        self.assertEqual(result.errors,[])
        self.assertEqual(origin.statistics()['downloaded_payload_bytes'],len(self.data))
        self.assertEqual(digest(self.src/'large.bin'),digest(self.dst/'large.bin'))

    def test_all_blocks_reused_without_file_requests(self):
        (self.ref/'copy').write_bytes(self.data)
        origin = DeltaSource(self.remote(),self.ref)
        with patch.object(origin.remote,'open_range',side_effect=AssertionError('Network data request unexpected')):
            self.assertEqual(self.transfer(origin).errors,[])
        self.assertEqual(origin.statistics()['downloaded_blocks'],0)

    def test_reference_corruption_falls_back_to_https(self):
        (self.ref/'copy').write_bytes(self.data)
        origin = DeltaSource(self.remote(),self.ref)
        (self.ref/'copy').write_bytes(b'x'*len(self.data))
        self.assertEqual(self.transfer(origin).errors,[])
        self.assertEqual(origin.statistics()['downloaded_payload_bytes'],len(self.data))

    def test_corrupt_remote_block_is_not_published(self):
        origin = DeltaSource(self.remote(),self.ref)
        with patch.object(origin.remote,'open_range',return_value=io.BytesIO(b'x'*BLOCK)):
            result = self.transfer(origin)
        self.assertTrue(result.errors)
        self.assertFalse((self.dst/'large.bin').exists())

    def test_interrupt_resume_with_reference_state(self):
        (self.ref/'copy').write_bytes(self.data)
        (self.ref/STATE).mkdir(); (self.ref/STATE/'journal').write_text('ignored')
        remote = self.remote()
        event = threading.Event()
        origin = DeltaSource(remote,self.ref,event)
        result = self.transfer(origin,event,lambda n,total: event.set() if n>=BLOCK*2 else None)
        self.assertTrue(result.errors)
        resumed = self.transfer(DeltaSource(remote,self.ref))
        self.assertEqual(resumed.errors,[])
        self.assertGreaterEqual(resumed.resumed_bytes,BLOCK*2)
        self.assertEqual((self.dst/'large.bin').read_bytes(),self.data)

    def test_compressed_ranges_and_arbitrary_read_offsets(self):
        origin = DeltaSource(self.remote('gzip'),self.ref)
        entry = next(e for e in origin.entries if e.path=='large.bin')
        with origin.open(entry,BLOCK-7) as stream:
            self.assertEqual(stream.read(BLOCK+19),self.data[BLOCK-7:2*BLOCK+12])
            self.assertEqual(stream.read(0),b'')
        self.assertEqual(self.transfer(origin).errors,[])

    def test_overlapping_reference_destination_is_rejected(self):
        origin = DeltaSource(self.remote(),self.ref)
        with self.assertRaises(TransferError):
            Transfer(origin,self.ref/'inside')
        with self.assertRaises(TransferError):
            Transfer(origin,self.base)

    def test_server_without_chunk_manifest_rejected(self):
        remote = self.remote(blocks=None)
        with self.assertRaisesRegex(TransferError,'--delta'):
            DeltaSource(remote,self.ref)

    def test_bad_chunk_manifest_rejected(self):
        remote = self.remote()
        remote.chunks['large.bin'] = ['0'*64]
        with self.assertRaises(TransferError):
            remote.validate_chunks()

    def test_range_overrun_is_rejected(self):
        from urllib.error import HTTPError
        remote = self.remote()
        entry=remote.entries[0]
        with self.assertRaises(HTTPError) as error:
            remote.open_range(entry,entry.size-1,2)
        self.assertEqual(error.exception.code,400)


if __name__ == '__main__':
    unittest.main()
