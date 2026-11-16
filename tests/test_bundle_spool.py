"""Research R4.3: wire equality, source safety and bounded producer failure."""
from dataclasses import replace
import errno
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.smallfile_bundle import BundleSource, CODECS, pack
from research.smallfile_bundle_r42 import pack as old_pack
from ultra.compression import ZSTD
from ultra.engine import TransferError


class SpoolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.src=self.root/'src';self.src.mkdir()
        (self.src/'vide').mkdir();(self.src/'.caché').write_bytes(b'')
        for i in range(17): (self.src/f'été-{i:02}').write_bytes(bytes([i])*65000)

    def test_all_codecs_same_wire_bytes_as_reference(self):
        for codec in CODECS:
            if codec in ('zstd1','zstd3','auto') and not ZSTD: continue
            for manifest in ('raw','deflate1'):
                with self.subTest(codec=codec,manifest=manifest):
                    a,b=self.root/'old',self.root/'new'
                    old_pack(self.src,a,codec=codec,manifest_codec=manifest,group_bytes=131072)
                    pack(self.src,b,codec=codec,manifest_codec=manifest,group_bytes=131072,spool=True)
                    self.assertEqual(a.read_bytes(),b.read_bytes())
                    source=BundleSource(b)
                    for e in source.entries:
                        if e.kind=='file':
                            with source.open(e) as stream:
                                self.assertEqual(stream.read(),(self.src/e.path).read_bytes())
                    a.unlink();b.unlink()

    def test_identity_index_rejects_forged_entry_fields(self):
        out=self.root/'out';pack(self.src,out,spool=True);source=BundleSource(out)
        entry=next(e for e in source.entries if e.kind=='file')
        for bad in (None, replace(entry,path=[]), replace(entry,size=entry.size+1),replace(entry,sha256='0'*64),
                    replace(entry,mtime_ns=entry.mtime_ns+1),replace(entry,mode=0),
                    replace(entry,path='missing')):
            with self.assertRaises(TransferError): source.open(bad)
        source.check(replace(entry))  # Equal immutable records are still accepted.

    def test_spool_disk_failure_does_not_publish_or_remove_old_output(self):
        out=self.root/'out';out.write_bytes(b'precious')
        with patch('research.smallfile_bundle._write_group',side_effect=OSError(errno.ENOSPC,'full')):
            with self.assertRaises(OSError): pack(self.src,out,spool=True)
        self.assertEqual(out.read_bytes(),b'precious')
        self.assertFalse((self.root/'out.part').exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),['out','src'])

    def test_source_changed_during_spooling_is_rejected(self):
        from research.smallfile_bundle import _write_group
        def changed(stream,group,codec):
            _write_group(stream,group,codec)
            (self.src/'été-00').write_bytes(b'changed')
        with patch('research.smallfile_bundle._write_group',side_effect=changed):
            with self.assertRaises(TransferError): pack(self.src,self.root/'out',spool=True)
        self.assertFalse((self.root/'out').exists())
        self.assertFalse((self.root/'out.part').exists())

    def test_spool_rejects_output_inside_source_and_keeps_existing_part(self):
        with self.assertRaises(TransferError): pack(self.src,self.src/'bad',spool=True)
        partial=self.root/'out.part';partial.write_bytes(b'keep')
        with self.assertRaises(FileExistsError): pack(self.src,self.root/'out',spool=True)
        self.assertEqual(partial.read_bytes(),b'keep')

    def test_empty_snapshot_and_option_validation(self):
        empty=self.root/'empty';empty.mkdir()
        out=self.root/'out';pack(empty,out,spool=True)
        self.assertEqual(BundleSource(out).entries,[])
        out.unlink()
        with self.assertRaises(ValueError): pack(empty,out,spool=1)
        self.assertFalse(out.exists())


    def test_spool_final_copy_error_cleans_only_own_temporary(self):
        out=self.root/'out';out.write_bytes(b'precious')
        def failed(src,dst,**kwargs):
            dst.write(b'partial')
            raise OSError(errno.ENOSPC,'full')
        with patch('research.smallfile_bundle.shutil.copyfileobj',side_effect=failed):
            with self.assertRaises(OSError): pack(self.src,out,spool=True)
        self.assertEqual(out.read_bytes(),b'precious')
        self.assertFalse((self.root/'out.part').exists())
