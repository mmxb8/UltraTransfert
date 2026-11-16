"""R4.2 compressed manifest robustness; research only."""
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import threading
import unittest
import zlib

from research.smallfile_bundle import (BundleSource, CodecError, MAGIC_V2,
    MANIFEST_HEADER, MAX_MANIFEST, _manifest_frame, _read_manifest, pack)
from ultra.engine import Options, Transfer, digest
from research.smallfile_bundle_r41 import BundleSource as LegacySource


class ManifestTests(unittest.TestCase):
    def frame(self, raw, payload=None, kind=1, size=None):
        payload = zlib.compress(raw) if payload is None else payload
        return MAGIC_V2 + MANIFEST_HEADER.pack(kind, len(raw) if size is None else size,
            len(payload), hashlib.sha256(raw).digest()) + payload

    def test_roundtrip_formats_and_raw_fallback(self):
        for raw in (b'', b'x', b'x'*MAX_MANIFEST):
            for codec in ('raw','deflate1'):
                self.assertEqual(_read_manifest(io.BytesIO(_manifest_frame(raw,codec))),raw)
        self.assertEqual(_manifest_frame(b'x','deflate1')[5],0)

    def test_bombs_sizes_unknown_codec_and_truncation(self):
        raw=b'x'*100000
        for frame in (self.frame(raw,size=1), self.frame(raw,size=MAX_MANIFEST+1),
                      self.frame(raw,kind=4), self.frame(raw)[:-1],
                      MAGIC_V2+MANIFEST_HEADER.pack(0,1,MAX_MANIFEST+1,b'0'*32),
                      b'UTSB9'):
            with self.subTest(frame=frame[:50]):
                with self.assertRaises(CodecError): _read_manifest(io.BytesIO(frame))

    def test_trailing_concatenated_and_invalid_streams(self):
        raw=b'{"entries":[],"groups":[]}'
        for payload in (zlib.compress(raw)+b'junk', zlib.compress(raw)*2,
                        b'not-zlib', zlib.compress(raw)[:-1]):
            with self.assertRaises(CodecError):
                _read_manifest(io.BytesIO(self.frame(raw,payload)))

    def test_checksum_and_raw_size(self):
        raw=b'hello'
        for frame in (self.frame(raw,b'wrong',kind=0),
                      self.frame(raw,zlib.compress(b'jello')),
                      self.frame(raw,b'hello',kind=0,size=4)):
            with self.assertRaises(CodecError): _read_manifest(io.BytesIO(frame))

    def test_identity_compatibility_and_verified_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/'src';src.mkdir()
            (src/'vide').mkdir();(src/'.caché').write_bytes(b'')
            for i in range(80): (src/f'été-{i}').write_bytes(b'content'*i)
            old,new=root/'old',root/'new'
            pack(src,old);pack(src,new,manifest_codec='deflate1')
            a,b=BundleSource(old),BundleSource(new)
            self.assertEqual(a.identity,b.identity)
            self.assertEqual(a.entries,LegacySource(old).entries)
            self.assertLess(new.stat().st_size,old.stat().st_size)
            result=Transfer(b,root/'out',Options(workers=1)).run()
            self.assertFalse(result.errors)
            for e in b.entries:
                if e.kind=='file': self.assertEqual(digest(src/e.path),digest(root/'out'/e.path))
            # Old readers explicitly reject new grammar.
            with self.assertRaises(CodecError): LegacySource(new)

    def test_compressed_manifest_keeps_path_and_duplicate_checks(self):
        for raw in (b'{"entries":[],"entries":[],"groups":[]}',
                    b'{"entries":[],"groups":[true]}'):
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'bad';p.write_bytes(_manifest_frame(raw,'deflate1'))
                with self.assertRaises((CodecError,ValueError)): BundleSource(p)

    def test_bad_option_never_publishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir()
            with self.assertRaises(ValueError): pack(src,root/'out',manifest_codec='unknown')
            self.assertFalse((root/'out').exists())


    def test_restore_resumes_across_manifest_representations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir()
            for i in range(8): (src/f'f-{i}').write_bytes(bytes([i])*65536)
            old,new=root/'old',root/'new'
            pack(src,old,group_bytes=65536)
            pack(src,new,group_bytes=65536,manifest_codec='deflate1')
            cancel=threading.Event()
            def stop(done,total):
                if done: cancel.set()
            first=Transfer(BundleSource(old),root/'out',Options(workers=1),
                           stop,cancel).run()
            self.assertTrue(first.errors)
            result=Transfer(BundleSource(new),root/'out',Options(workers=1)).run()
            self.assertFalse(result.errors)
            for i in range(8):
                self.assertEqual(digest(src/f'f-{i}'),digest(root/'out'/f'f-{i}'))
