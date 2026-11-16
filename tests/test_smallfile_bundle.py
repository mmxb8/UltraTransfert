import errno
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch

from research.smallfile_bundle import (BundleSource, CODECS, CodecError, HEADER,
                                      MAGIC, MAX_MANIFEST, pack)
from ultra.compression import ZSTD
from ultra.engine import LocalSource, Options, Transfer, TransferError, inventory


class SmallBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.src = self.base/'source'; self.src.mkdir()
        (self.src/'dossier vide').mkdir(); (self.src/'.caché').write_bytes(b'')
        (self.src/'été.txt').write_bytes(('Bonjour Maher! '*200).encode())
        (self.src/'z.bin').write_bytes(bytes(range(256))*240)
        self.bundle = self.base/'group.utb'

    def test_roundtrip_codecs_and_bounded_groups(self):
        for codec in CODECS:
            if codec.startswith(('zstd','auto')) and not ZSTD: continue
            path = self.base/(codec+'.utb')
            metrics = pack(self.src, path, codec=codec, group_files=1)
            self.assertEqual(metrics['groups'], 3)
            source = BundleSource(path)
            result = Transfer(source, self.base/codec, Options(workers=1)).run()
            self.assertFalse(result.errors)
            self.assertEqual({e.path:e.kind for e in inventory(self.src)},
                             {e.path:e.kind for e in inventory(self.base/codec, exclude_state=True)})
            for e in inventory(self.src):
                if e.kind == 'file': self.assertEqual((self.src/e.path).read_bytes(),(self.base/codec/e.path).read_bytes())

    def test_empty_tree_and_empty_files(self):
        (self.src/'été.txt').unlink(); (self.src/'z.bin').unlink()
        pack(self.src, self.bundle, codec='raw'); source = BundleSource(self.bundle)
        self.assertFalse(Transfer(source, self.base/'empty').run().errors)
        (self.src/'.caché').unlink(); (self.src/'dossier vide').rmdir()
        pack(self.src, self.base/'zero', codec='raw')
        self.assertEqual(BundleSource(self.base/'zero').entries, [])

    def test_no_overwrite_or_staging_loss(self):
        self.bundle.write_bytes(b'precious')
        with self.assertRaises(FileExistsError): pack(self.src, self.bundle)
        self.assertEqual(self.bundle.read_bytes(), b'precious')
        self.assertFalse(self.bundle.with_name('group.utb.part').exists())
        self.bundle.unlink(); staging=self.bundle.with_name('group.utb.part'); staging.write_bytes(b'keep')
        with self.assertRaises(FileExistsError): pack(self.src, self.bundle)
        self.assertEqual(staging.read_bytes(),b'keep')

    def test_corruption_truncation_and_trailing(self):
        pack(self.src, self.bundle, codec='raw'); raw=self.bundle.read_bytes()
        for bad in (raw[:-1],raw+b'x',raw[:-1]+bytes([raw[-1]^1]),b'bad'):
            self.bundle.write_bytes(bad)
            with self.assertRaises((CodecError,ValueError)): BundleSource(self.bundle)

    def rewrite_manifest(self, change):
        raw=self.bundle.read_bytes(); n=struct.unpack('!I',raw[5:9])[0]
        manifest=json.loads(raw[9:9+n]); change(manifest)
        data=json.dumps(manifest).encode()
        self.bundle.write_bytes(MAGIC+struct.pack('!I',len(data))+data+raw[9+n:])

    def test_path_traversal_and_collision(self):
        for change in (lambda m:m['entries'][0].update(path='../escape'),
                       lambda m:m['entries'].append(m['entries'][0])):
            self.bundle.unlink(missing_ok=True); pack(self.src,self.bundle,codec='raw')
            self.rewrite_manifest(change)
            with self.assertRaises(TransferError): BundleSource(self.bundle)
        self.assertFalse((self.base/'escape').exists())

    def test_bounds_before_payload_allocation(self):
        self.bundle.write_bytes(MAGIC+struct.pack('!I',MAX_MANIFEST+1))
        with self.assertRaises(CodecError): BundleSource(self.bundle)
        self.bundle.unlink();pack(self.src,self.bundle,codec='raw')
        self.rewrite_manifest(lambda m:m.update(groups=[2**31]))
        with self.assertRaises(CodecError): BundleSource(self.bundle)

    def test_malformed_types_and_duplicate_keys(self):
        pack(self.src,self.bundle,codec='raw')
        self.rewrite_manifest(lambda m:m['entries'][0].update(size=True))
        with self.assertRaises(CodecError): BundleSource(self.bundle)
        data=b'{"entries":[],"entries":[],"groups":[]}'
        self.bundle.write_bytes(MAGIC+struct.pack('!I',len(data))+data)
        with self.assertRaises(CodecError): BundleSource(self.bundle)

    def test_source_links_large_files_and_output_inside_source(self):
        (self.src/'link').symlink_to(self.src/'été.txt')
        with self.assertRaises(TransferError): pack(self.src,self.bundle)
        (self.src/'link').unlink(); (self.src/'big').write_bytes(b'x'*65537)
        with self.assertRaises(CodecError): pack(self.src,self.bundle)
        (self.src/'big').unlink()
        with self.assertRaises(TransferError): pack(self.src,self.src/'out')

    def test_source_changes_are_detected(self):
        original=LocalSource.check_all
        def changed(source, cancel=None):
            (self.src/'été.txt').write_bytes(b'changed')
            original(source,cancel)
        with patch.object(LocalSource,'check_all',changed):
            with self.assertRaises(TransferError): pack(self.src,self.bundle)
        self.assertFalse(self.bundle.exists())

    def test_rehydration_interrupt_resume_and_conflict(self):
        pack(self.src,self.bundle); source=BundleSource(self.bundle)
        cancel=threading.Event()
        def progress(done,total):
            if done: cancel.set()
        dest=self.base/'resume'
        first=Transfer(source,dest,Options(workers=1),progress,cancel).run()
        self.assertTrue(first.errors)
        resumed=Transfer(BundleSource(self.bundle),dest,Options(workers=1)).run()
        self.assertFalse(resumed.errors)
        (dest/'été.txt').write_bytes(b'conflict')
        self.assertTrue(Transfer(BundleSource(self.bundle),dest).run().errors)
        self.assertEqual((dest/'été.txt').read_bytes(),b'conflict')

    def test_no_space_rehydration(self):
        pack(self.src,self.bundle)
        from collections import namedtuple
        usage=namedtuple('usage','total used free')(0,0,0)
        with patch('ultra.engine.shutil.disk_usage',return_value=usage):
            with self.assertRaisesRegex(TransferError, 'Espace insuffisant'):
                Transfer(BundleSource(self.bundle),self.base/'full').run()
        self.assertFalse((self.base/'full'/'été.txt').exists())

    def test_lzma_expansion_bound(self):
        import lzma
        payload=lzma.compress(b'x'*100000,preset=1)
        from research.smallfile_bundle import _decode
        with self.assertRaises(CodecError): _decode(3,payload,1)

    def test_https_container_interrupt_resume_and_authentication(self):
        import secrets
        import subprocess
        from ultra.network import RemoteSource, make_server
        cert,key=self.base/'cert.pem',self.base/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        import random
        rng=random.Random(771)
        for i in range(8): (self.src/f'noise-{i}').write_bytes(rng.randbytes(65536))
        serving=self.base/'serving';serving.mkdir()
        pack(self.src,serving/'snapshot.utb',codec='raw',group_bytes=65536)
        token=secrets.token_urlsafe(48)
        server=make_server(LocalSource(serving),('127.0.0.1',0),cert,key,token)
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        try:
            url=f'https://localhost:{server.server_port}'
            from urllib.error import HTTPError
            with self.assertRaises(HTTPError) as caught: RemoteSource(url,'wrong'*10,cert)
            self.assertEqual(caught.exception.code,401)
            remote=RemoteSource(url,token,cert)
            cancel=threading.Event()
            def stop(done,total):
                if done>=65536: cancel.set()
            dest=self.base/'network'
            first=Transfer(remote,dest,Options(workers=1,buffer_size=65536),stop,cancel).run()
            self.assertTrue(first.errors)
            second=Transfer(RemoteSource(url,token,cert),dest,Options(workers=1,buffer_size=65536)).run()
            self.assertFalse(second.errors);self.assertGreaterEqual(second.resumed_bytes,65536)
            restored=Transfer(BundleSource(dest/'snapshot.utb'),self.base/'restored').run()
            self.assertFalse(restored.errors)
            self.assertEqual((self.base/'restored'/'noise-7').read_bytes(),(self.src/'noise-7').read_bytes())
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

    def test_cross_group_file_and_manifest_hash_are_rejected(self):
        import shutil
        shutil.rmtree(self.src);self.src.mkdir()
        (self.src/'a').write_bytes(b'a');(self.src/'b').write_bytes(b'b')
        pack(self.src,self.bundle,codec='raw',group_files=1)
        def split(m):
            m['entries'][0].update(size=2,sha256=hashlib.sha256(b'ab').hexdigest())
            m['entries'][1].update(size=0,sha256=hashlib.sha256(b'').hexdigest())
        self.rewrite_manifest(split)
        with self.assertRaisesRegex(CodecError,'boundary'): BundleSource(self.bundle)
        self.bundle.unlink();pack(self.src,self.bundle,codec='raw')
        self.rewrite_manifest(lambda m:m['entries'][0].update(sha256='0'*64))
        with self.assertRaisesRegex(CodecError,'Corrupt file'): BundleSource(self.bundle)
