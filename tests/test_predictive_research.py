import hashlib
import io
import json
import random
import struct
import unittest
from unittest.mock import patch

from research.predictive_compression import (MAGIC, WIDTHS, PREDICTORS, PredictiveEncoder,
                                             CodecError, frame, header, predict, unframe)
from ultra.blockstream import BlockReader, write_stream
from ultra.compression import MAX_BLOCK, MAX_FRAME, ZSTD


class PredictiveResearchTests(unittest.TestCase):
    def test_predictors_arbitrary_sizes_and_unaligned_tails(self):
        rng=random.Random(4415)
        for size in (0,1,2,3,7,15,16,17,31,257,4099,65537):
            data=rng.randbytes(size)
            for width in WIDTHS:
                for kind in PREDICTORS:
                    with self.subTest(size=size,width=width,kind=kind):
                        self.assertEqual(predict(predict(data,width,kind),width,kind,True),data)

    def test_division_inverse_matches_prefix_doubling(self):
        rng=random.Random(914)
        for size in (17,4099,65537,MAX_BLOCK):
            data=rng.randbytes(size)
            for width in WIDTHS:
                encoded=predict(data,width,'subtract')
                self.assertEqual(predict(encoded,width,'subtract',True),data)
                self.assertEqual(predict(encoded,width,'subtract',True,inversion='doubling'),data)

    def test_known_subtract_vector_and_edge_values(self):
        self.assertEqual(predict(b'\x00\x01\x02\x03',1,'subtract'),b'\x00\x01\x01\x01')
        for data in (b'\0'*1025,b'\xff'*1025,bytes(range(256))*4):
            for w in WIDTHS:
                self.assertEqual(predict(predict(data,w,'subtract'),w,'subtract',True),data)

    def test_all_frame_recipes(self):
        data=random.Random(45).randbytes(65537)
        for codec in ('raw','zlib1')+(('zstd1','zstd3') if ZSTD else ()):
            for w in WIDTHS:
                for p in PREDICTORS:
                    self.assertEqual(unframe(frame(data,(codec,w,p),fallback=False)),data)

    def test_corruption_truncation_and_trailing(self):
        f=frame(b'hello'*10000,('zlib1',4,'subtract'))
        corrupt=bytearray(f);corrupt[-1]^=1
        for bad in (f[:-1],f+b'junk',bytes(corrupt),f[:8],b'wrong'+f[5:]):
            with self.assertRaises((CodecError,ValueError)):
                unframe(bad)

    def test_bad_headers_and_recipe_cannot_execute_code(self):
        base={'size':0,'codec':'raw','width':1,'predictor':'none','sha256':hashlib.sha256(b'').hexdigest()}
        for key,value in (('size',True),('size',MAX_BLOCK+1),('size',-1),('width',3),('width',True),
                          ('codec','eval'),('predictor','__import__'),('sha256','x')):
            h=json.dumps({**base,key:value}).encode()
            with self.assertRaises(CodecError):unframe(MAGIC+struct.pack('!I',len(h))+h)
        with self.assertRaises(CodecError):unframe(MAGIC+struct.pack('!I',4097))
        with self.assertRaises(CodecError):unframe(b'x'*(MAX_FRAME+1))

    def test_duplicate_header_keys_rejected(self):
        h=b'{"size":0,"size":1}'
        with self.assertRaises(CodecError):unframe(MAGIC+struct.pack('!I',len(h))+h)

    def test_adaptive_noise_exit_and_raw_size_limit(self):
        data=random.Random(492).randbytes(200003)
        encoder=PredictiveEncoder(50)
        encoded=encoder.encode(data)
        self.assertEqual(encoder.recipe,('raw',1,'none'))
        self.assertEqual(unframe(encoded),data)
        self.assertLessEqual(len(encoded),len(frame(data)))

    def test_recipe_reuse_content_change_and_periodic_search(self):
        e=PredictiveEncoder(50,retune_every=3)
        data=b'abcde'*20000
        for _ in range(3):self.assertEqual(unframe(e.encode(data)),data)
        self.assertEqual(e.searches,1)
        noise=random.Random(29).randbytes(len(data))
        self.assertEqual(unframe(e.encode(noise)),noise)
        self.assertEqual(e.recipe,('raw',1,'none'))
        self.assertEqual(unframe(e.encode(data)),data)
        self.assertGreater(e.searches,2)

    def test_multiblock_in_research_harness_with_terminal_checks(self):
        data=b'abcdefgh'*(MAX_BLOCK//8)+b'end'
        output=io.BytesIO()
        write_stream(io.BytesIO(data),output,len(data),PredictiveEncoder(50))
        encoded=output.getvalue()
        with patch('ultra.blockstream.unframe',unframe):
            self.assertEqual(BlockReader(io.BytesIO(encoded),len(data)).read(len(data)+1),data)
            with self.assertRaises(CodecError):
                BlockReader(io.BytesIO(encoded[:-1]),len(data)).read(len(data)+1)

    def test_config_and_block_limits(self):
        for args in ((0,),(-1,),(float('nan'),),(float('inf'),),(10,['zstd1'])):
            with self.assertRaises(CodecError):PredictiveEncoder(*args)
        with self.assertRaises(CodecError):PredictiveEncoder(1,retune_every=0)
        with self.assertRaises(CodecError):frame(b'x'*(MAX_BLOCK+1))
        with self.assertRaises(CodecError):PredictiveEncoder().encode(b'x'*(MAX_BLOCK+1))

    def test_codec_negotiation_restricts_research_candidates(self):
        e=PredictiveEncoder(10,['raw','zlib1'])
        self.assertEqual(unframe(e.encode(b'hello'*10000)),b'hello'*10000)
        self.assertNotIn(e.recipe[0],('zstd1','zstd3'))

    def test_decoder_bounds_output_and_old_decoder_rejects_research_frame(self):
        import zlib
        from ultra.compression import unframe as released_decoder
        base={'size':1,'codec':'zlib1','width':1,'predictor':'none','sha256':hashlib.sha256(b'a').hexdigest()}
        h=json.dumps(base).encode()
        with self.assertRaises(CodecError):
            unframe(MAGIC+struct.pack('!I',len(h))+h+zlib.compress(b'a'*1000000))
        with self.assertRaises(CodecError):released_decoder(frame(b'abc'))


class PredictiveHTTPSResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import shutil,subprocess,tempfile
        from pathlib import Path
        if not shutil.which('openssl'):raise unittest.SkipTest('openssl unavailable')
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.cert=cls.root/'cert.pem';cls.key=cls.root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.key),
                        '-out',str(cls.cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        import tempfile,threading
        from pathlib import Path
        from ultra.engine import LocalSource
        from ultra.network import make_server
        self.tmpcase=tempfile.TemporaryDirectory(dir=self.root)
        self.base=Path(self.tmpcase.name);self.source=self.base/'source';self.source.mkdir()
        self.data=bytes(range(256))*(MAX_BLOCK//256+113)+b'tail'
        (self.source/'été.bin').write_bytes(self.data)
        (self.source/'vide').write_bytes(b'');(self.source/'dossier vide').mkdir()
        self.token='research-test-'+('x'*48)
        self.server=make_server(LocalSource(self.source),('127.0.0.1',0),self.cert,self.key,self.token,'ultra')
        self.thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=.01),daemon=True)
        self.thread.start();self.url=f'https://localhost:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5);self.tmpcase.cleanup()

    def test_actual_tls_interrupt_resume_and_non_aligned_range(self):
        import threading
        from research.benchmark_predictive_https import Encoder
        from ultra.engine import Options,Transfer,digest
        from ultra.network import RemoteSource
        stop=threading.Event();dest=self.base/'received'
        with patch('ultra.network.AdaptiveEncoder',side_effect=lambda *a,**kw:Encoder('fixed-subtract4-zstd3' if ZSTD else 'predictive',50)), \
             patch('ultra.blockstream.unframe',unframe):
            remote=RemoteSource(self.url,self.token,self.cert,'ultra')
            first=Transfer(remote,dest,Options(workers=1,buffer_size=65536),
                           cancel=stop,progress=lambda n,total:stop.set() if n>=65536 else None).run()
            self.assertTrue(first.errors)
            second=Transfer(remote,dest,Options(workers=1,buffer_size=65536)).run()
            self.assertFalse(second.errors,second.errors)
            self.assertGreater(second.resumed_bytes,0)
            self.assertEqual(digest(dest/'été.bin'),hashlib.sha256(self.data).hexdigest())
            self.assertTrue((dest/'dossier vide').is_dir());self.assertEqual((dest/'vide').read_bytes(),b'')
            entry=next(e for e in remote.entries if e.path=='été.bin')
            with remote.open_range(entry,17,100003) as stream:
                self.assertEqual(stream.read(100004),self.data[17:100020])
            remote.release_connections()

    def test_corrupt_predictive_frame_is_not_published(self):
        from ultra.engine import Options,Transfer
        from ultra.network import RemoteSource
        class BadEncoder:
            searches=reused=0
            def encode(self,data):
                encoded=bytearray(frame(data));encoded[-1]^=1;return bytes(encoded)
        with patch('ultra.network.AdaptiveEncoder',side_effect=lambda *a,**kw:BadEncoder()), \
             patch('ultra.blockstream.unframe',unframe):
            remote=RemoteSource(self.url,self.token,self.cert,'ultra')
            dest=self.base/'corrupt'
            result=Transfer(remote,dest,Options(workers=1)).run()
            self.assertTrue(result.errors)
            self.assertFalse((dest/'été.bin').exists())


if __name__=='__main__':unittest.main()
