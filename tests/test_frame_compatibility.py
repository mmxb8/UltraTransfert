"""Same bytes on the wire and strict decoder checks after frame optimization."""
import random
import unittest
from unittest.mock import patch

from research.benchmark_frame_cost import LegacyZstd, legacy_frame
from ultra import compression, predictive


class FrameCompatibilityTests(unittest.TestCase):
    def test_predictive_frames_match_reference_with_and_without_fallback(self):
        rng=random.Random(820117)
        for size in (0,1,17,4099,65537):
            for data in (rng.randbytes(size),(b'abcde'*((size+4)//5))[:size]):
                for codec in compression.codecs():
                    for width in (1,4,16):
                        for predictor in ('none','xor','subtract'):
                            for fallback in (True,False):
                                recipe=codec,width,predictor
                                with self.subTest(size=size,recipe=recipe,fallback=fallback):
                                    old=legacy_frame(data,recipe,fallback=fallback)
                                    new=predictive.frame(data,recipe,fallback=fallback)
                                    self.assertEqual(new,old)
                                    self.assertEqual(predictive.unframe(new),data)

    def test_fallback_counts_header_bytes_and_rejects_corruption(self):
        data=random.Random(718).randbytes(4001)
        with patch('ultra.predictive.compress',return_value=data[:-1]):
            encoded=predictive.frame(data,('zlib1',4,'none'))
        self.assertEqual(encoded,predictive.frame(data))
        self.assertEqual(predictive.unframe(encoded),data)
        with self.assertRaises(compression.CodecError):
            predictive.unframe(encoded[:-1]+bytes([encoded[-1]^1]))

    @unittest.skipUnless(compression.ZSTD,'System Zstandard unavailable')
    def test_native_output_matches_reference_and_bounds_stay_strict(self):
        old=LegacyZstd();new=compression.ZSTD
        rng=random.Random(219)
        for size in (0,1,4099,compression.MAX_BLOCK):
            for data in (rng.randbytes(size),b'\0'*size):
                for level in (1,3):
                    encoded=new.compress(data,level)
                    self.assertEqual(encoded,old.compress(data,level))
                    self.assertEqual(new.decompress(encoded,size),data)
                    for bad,size_expected in ((encoded+b'junk',size),(encoded[:-1],size),(encoded,size+1)):
                        with self.assertRaises(compression.CodecError):
                            new.decompress(bad,size_expected)
