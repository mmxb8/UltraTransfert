import hashlib
import io
import json
import random
import struct
import unittest
from unittest.mock import patch

from ultra.blockstream import write_stream, BlockReader, MAGIC
from ultra.compression import MAX_BLOCK, MAX_FRAME, CodecError
from research.predictive_compression import frame, unframe
from research.stream_reader_r3 import LeanBlockReader, raw_view_unframe


class RawEncoder:
    searches=reused=0
    def encode(self,data):return frame(data)


class Fragmented(io.BytesIO):
    def read(self,n=-1):return super().read(min(n,137))


class ReaderResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=random.Random(8173).randbytes(MAX_BLOCK+271)
        out=io.BytesIO();write_stream(io.BytesIO(cls.data),out,len(cls.data),RawEncoder())
        cls.encoded=out.getvalue()

    def test_full_and_fragmented_reads_across_boundaries(self):
        for stream in (io.BytesIO,Fragmented):
            with patch('ultra.blockstream.unframe',raw_view_unframe):
                reader=LeanBlockReader(stream(self.encoded),len(self.data))
                self.assertEqual(reader.read(0),b'')
                offset=0
                for n in (19,65536,MAX_BLOCK-65556,11,200,999):
                    got=reader.read(n)
                    self.assertIs(type(got),bytes)
                    self.assertEqual(got,self.data[offset:offset+n]);offset+=len(got)
                self.assertEqual(reader.read(MAX_BLOCK),self.data[offset:])
                self.assertEqual(reader.read(1),b'')

    def test_readinto_and_final_terminal_before_return(self):
        for stream in (io.BytesIO,Fragmented):
            with patch('ultra.blockstream.unframe',raw_view_unframe):
                reader=LeanBlockReader(stream(self.encoded),len(self.data))
                target=bytearray(MAX_BLOCK+500)
                self.assertEqual(reader.readinto(target),len(self.data))
                self.assertEqual(target[:len(self.data)],self.data)
                self.assertEqual(reader.readinto(target),0)
                bad=LeanBlockReader(stream(self.encoded[:-1]),len(self.data))
                unchanged=bytearray(b'z'*(len(self.data)+1))
                with self.assertRaises(CodecError):bad.readinto(unchanged)
                self.assertEqual(unchanged,b'z'*len(unchanged))

    def test_invalid_terminal_corruption_lengths_and_trailing(self):
        damaged=bytearray(self.encoded);damaged[200]^=1
        bad_terminal=bytearray(self.encoded);bad_terminal[-1]^=1
        for wire in (self.encoded[:-1],self.encoded[:-44],self.encoded+b'x',bytes(damaged),bytes(bad_terminal)):
            with patch('ultra.blockstream.unframe',raw_view_unframe),self.assertRaises(CodecError):
                LeanBlockReader(io.BytesIO(wire),len(self.data)).read(len(self.data)+1)
        for size in (len(self.data)-1,len(self.data)+1):
            with patch('ultra.blockstream.unframe',raw_view_unframe),self.assertRaises(CodecError):
                LeanBlockReader(io.BytesIO(self.encoded),size).read(len(self.data)+2)

    def test_zero_length_and_invalid_read_sizes(self):
        out=io.BytesIO();write_stream(io.BytesIO(b''),out,0,RawEncoder())
        r=LeanBlockReader(Fragmented(out.getvalue()),0)
        self.assertEqual(r.read(1),b'');self.assertTrue(r.finished)
        for n in (-1,True,1.5,None):
            with self.assertRaises(CodecError):r.read(n)

    def test_oversize_frame_before_body_read(self):
        data=MAGIC+struct.pack('!I',MAX_FRAME+1)
        with self.assertRaises(CodecError):LeanBlockReader(Fragmented(data),1).read(1)

    def test_view_decoder_exact_and_same_validation(self):
        for n in (0,1,3,65537,MAX_BLOCK):
            data=self.data[:n];encoded=frame(data)
            view=raw_view_unframe(encoded)
            self.assertIsInstance(view,memoryview);self.assertTrue(view.readonly)
            self.assertEqual(bytes(view),data)
            for bad in (encoded[:-1],encoded+b'x'):
                with self.assertRaises(CodecError):raw_view_unframe(bad)
        for recipe in (('raw',4,'subtract'),('zlib1',1,'none'),('zlib1',4,'xor')):
            f=frame(self.data[:65537],recipe,fallback=False)
            self.assertEqual(raw_view_unframe(f),unframe(f))

    def test_malformed_header_rejected_by_view_path(self):
        from research.predictive_compression import MAGIC as PMAGIC
        h={'size':3,'codec':'raw','width':1,'predictor':'none','sha256':hashlib.sha256(b'abc').hexdigest()}
        for key,value in (('size',True),('size',MAX_BLOCK+1),('sha256','x'),('predictor','eval')):
            hdr=json.dumps({**h,key:value}).encode()
            with self.assertRaises(CodecError):raw_view_unframe(PMAGIC+struct.pack('!I',len(hdr))+hdr+b'abc')
        hdr=b'{"size":3,"size":3}'
        with self.assertRaises(CodecError):raw_view_unframe(PMAGIC+struct.pack('!I',len(hdr))+hdr+b'abc')


import test_predictive_research as previous


class ReaderHTTPS(unittest.TestCase):
    setUpClass=classmethod(previous.PredictiveHTTPSResearchTests.setUpClass.__func__)
    tearDownClass=classmethod(previous.PredictiveHTTPSResearchTests.tearDownClass.__func__)
    setUp=previous.PredictiveHTTPSResearchTests.setUp
    tearDown=previous.PredictiveHTTPSResearchTests.tearDown

    def test_tls_resume_and_range_with_lean_reader(self):
        import threading
        from research.budget_compression import BudgetEncoder
        from ultra.engine import Transfer,Options,digest
        from ultra.network import RemoteSource
        dest=self.base/'lean-received';stop=threading.Event()
        with patch('ultra.network.AdaptiveEncoder',side_effect=lambda *a,**kw:BudgetEncoder(50)), \
             patch('ultra.network.BlockReader',LeanBlockReader),patch('ultra.blockstream.unframe',raw_view_unframe):
            remote=RemoteSource(self.url,self.token,self.cert,'ultra')
            first=Transfer(remote,dest,Options(workers=1,buffer_size=65536),cancel=stop,
                           progress=lambda n,t:stop.set() if n>=65536 else None).run()
            self.assertTrue(first.errors)
            result=Transfer(remote,dest,Options(workers=1)).run()
            self.assertFalse(result.errors,result.errors);self.assertGreater(result.resumed_bytes,0)
            self.assertEqual(digest(dest/'été.bin'),hashlib.sha256(self.data).hexdigest())
            self.assertTrue((dest/'dossier vide').is_dir());self.assertEqual((dest/'vide').read_bytes(),b'')
            entry=next(e for e in remote.entries if e.path=='été.bin')
            with remote.open_range(entry,17,100003) as stream:self.assertEqual(stream.read(100004),self.data[17:100020])
            remote.release_connections()

    def test_tls_bad_block_is_not_published(self):
        from ultra.engine import Transfer,Options
        from ultra.network import RemoteSource
        class Corrupt(RawEncoder):
            def encode(self,data):
                wire=bytearray(super().encode(data));wire[-1]^=1;return bytes(wire)
        with patch('ultra.network.AdaptiveEncoder',side_effect=lambda *a,**kw:Corrupt()), \
             patch('ultra.network.BlockReader',LeanBlockReader),patch('ultra.blockstream.unframe',raw_view_unframe):
            remote=RemoteSource(self.url,self.token,self.cert,'ultra');dest=self.base/'bad'
            result=Transfer(remote,dest,Options(workers=1)).run()
            self.assertTrue(result.errors);self.assertFalse((dest/'été.bin').exists())
            remote.release_connections()
