import hashlib
import json
import math
import random
import struct
import unittest
import zlib

from research.compression import MAGIC,MAX_BLOCK,CodecError,ZSTD,adaptive_frame,codecs,frame,shuffle,unframe


class CompressionLabTests(unittest.TestCase):
    def test_all_recipes_exact_on_arbitrary_lengths(self):
        rng=random.Random(991)
        for size in (0,1,3,17,255,1027,65537):
            data=rng.randbytes(size)
            for width in (1,2,4,8,16):
                for codec in codecs():
                    with self.subTest(size=size,width=width,codec=codec):
                        self.assertEqual(unframe(frame(data,codec,width)),data)

    def test_adaptive_roundtrip_for_link_speeds(self):
        data=b'abc123'*20000
        for rate in (1,100,10000):
            encoded,stats=adaptive_frame(data,rate)
            self.assertEqual(unframe(encoded),data)
            self.assertGreater(stats['selection_seconds'],0)
            self.assertLessEqual(len(encoded),len(frame(data)))

    def test_incompressible_fallback_limits_size(self):
        data=random.Random(16).randbytes(200000)
        encoded,stats=adaptive_frame(data,10000)
        self.assertEqual(unframe(encoded),data)
        self.assertLessEqual(len(encoded),len(frame(data)))

    def test_corruption_detected(self):
        encoded=bytearray(frame(b'hello'*1000,'raw',1))
        encoded[-1]^=1
        with self.assertRaises(CodecError):unframe(bytes(encoded))

    def test_truncated_frames(self):
        encoded=frame(b'hello'*1000,'zlib1',4)
        for cut in (0,1,4,9,32,len(encoded)-1):
            with self.subTest(cut=cut),self.assertRaises(CodecError):unframe(encoded[:cut])

    def make_header(self,header,payload=b''):
        raw=json.dumps(header).encode()
        return MAGIC+struct.pack('!I',len(raw))+raw+payload

    def test_hostile_sizes_and_widths(self):
        base={'size':0,'width':1,'codec':'raw','sha256':hashlib.sha256(b'').hexdigest()}
        for key,value in (('size',-1),('size',MAX_BLOCK+1),('size',True),('width',3),('codec','pickle'),('sha256','x')):
            with self.subTest(key=key,value=value),self.assertRaises(CodecError):
                unframe(self.make_header({**base,key:value}))

    def test_bounded_decompression(self):
        base={'size':1,'width':1,'codec':'zlib1','sha256':hashlib.sha256(b'a').hexdigest()}
        with self.assertRaises(CodecError):
            unframe(self.make_header(base,zlib.compress(b'a'*1000000)))

    def test_trailing_compressed_stream_rejected(self):
        for codec in codecs():
            with self.subTest(codec=codec),self.assertRaises(CodecError):
                unframe(frame(b'abc'*1000,codec)+b'junk')

    def test_invalid_bandwidth(self):
        for value in (0,-1,float('inf'),float('nan')):
            with self.assertRaises(CodecError):adaptive_frame(b'test',value)

    def test_block_limit(self):
        with self.assertRaises(CodecError):frame(b'x'*(MAX_BLOCK+1))


if __name__=='__main__':unittest.main()
