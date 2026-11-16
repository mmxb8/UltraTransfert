import hashlib
import io
import random
import struct
import unittest
from unittest.mock import patch

from ultra.blockstream import MAGIC, BlockReader, write_stream
from ultra.compression import AdaptiveEncoder, CodecError, MAX_BLOCK, MAX_FRAME, codecs, frame, unframe


class BlockStreamTests(unittest.TestCase):
    def encode(self, data, encoder=None):
        stream = io.BytesIO()
        count = write_stream(io.BytesIO(data), stream, len(data), encoder)
        self.assertEqual(count, len(stream.getvalue()))
        return stream.getvalue()

    def test_multiblock_arbitrary_reads_and_readinto(self):
        data = (bytes(range(256)) * (MAX_BLOCK//256+3)) + b'end'
        encoded = self.encode(data)
        reader = BlockReader(io.BytesIO(encoded), len(data))
        self.assertEqual(reader.read(0), b'')
        self.assertEqual(reader.read(MAX_BLOCK-7), data[:MAX_BLOCK-7])
        buffer = bytearray(19)
        self.assertEqual(reader.readinto(buffer),19)
        self.assertEqual(bytes(buffer),data[MAX_BLOCK-7:MAX_BLOCK+12])
        self.assertEqual(reader.read(MAX_BLOCK+1),data[MAX_BLOCK+12:])
        self.assertEqual(reader.read(1),b'')

    def test_empty_stream_requires_terminal(self):
        data = self.encode(b'')
        self.assertEqual(BlockReader(io.BytesIO(data),0).read(1),b'')
        with self.assertRaises(CodecError):
            BlockReader(io.BytesIO(data[:-1]),0).read(1)

    def test_corruption_truncation_trailing_and_total(self):
        data = b'abc'*10000
        encoded = self.encode(data)
        corrupt = bytearray(encoded); corrupt[-1] ^= 1
        for variant in (encoded[:-1],encoded[:-44],encoded+b'junk',bytes(corrupt),b'wrong'+encoded[5:]):
            with self.subTest(size=len(variant)),self.assertRaises(CodecError):
                BlockReader(io.BytesIO(variant),len(data)).read(len(data)+1)
        for length in (len(data)-1,len(data)+1):
            with self.assertRaises(CodecError):
                BlockReader(io.BytesIO(encoded),length).read(len(data)+1)

    def test_frame_length_is_bounded_before_read(self):
        encoded = MAGIC + struct.pack('!I',MAX_FRAME+1)
        with self.assertRaisesRegex(CodecError,'volumineuse'):
            BlockReader(io.BytesIO(encoded),1).read(1)

    def test_empty_nonterminal_block_rejected(self):
        empty = frame(b'')
        encoded = MAGIC+struct.pack('!I',len(empty))+empty
        with self.assertRaises(CodecError):
            BlockReader(io.BytesIO(encoded),0).read(1)

    def test_truncated_source_cannot_emit_success_terminal(self):
        with self.assertRaises(CodecError):
            write_stream(io.BytesIO(b'abc'),io.BytesIO(),4)

    def test_recipe_reuse_and_reprofile_on_content_change(self):
        encoder = AdaptiveEncoder(10,retune_every=16)
        data = b'abcd'*65536
        for _ in range(4):
            self.assertEqual(unframe(encoder.encode(data)),data)
        self.assertEqual(encoder.searches,1)
        self.assertEqual(encoder.reused,3)
        noise = random.Random(19).randbytes(len(data))
        self.assertEqual(unframe(encoder.encode(noise)),noise)
        self.assertEqual(encoder.recipe,('raw',1))
        self.assertEqual(unframe(encoder.encode(data)),data)
        self.assertGreater(encoder.searches,1)

    def test_peer_without_zstd_and_no_zstd_runtime(self):
        with patch('ultra.compression.ZSTD',None):
            data = b'data'*20000
            encoder=AdaptiveEncoder(10,['raw','zlib1'])
            self.assertEqual(unframe(encoder.encode(data)),data)
            self.assertNotIn(encoder.recipe[0],('zstd1','zstd3'))

    def test_periodic_search_and_bad_configuration(self):
        encoder = AdaptiveEncoder(10,retune_every=2)
        for _ in range(5):encoder.encode(b'abc'*3000)
        self.assertEqual(encoder.searches,3)
        for args in ((0,),(-1,),(float('nan'),),(float('inf'),),(10,['zlib1'])):
            with self.assertRaises(CodecError):AdaptiveEncoder(*args)
