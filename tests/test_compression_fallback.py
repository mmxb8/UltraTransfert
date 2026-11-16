"""Cas de retour au brut : format existant et contrôles toujours applicables."""
import hashlib
import importlib.util
import random
from pathlib import Path
import unittest
from unittest.mock import patch

from ultra.compression import AdaptiveEncoder, CodecError, codecs, frame, unframe


class CompressionFallbackTests(unittest.TestCase):
    def test_frames_compatible_with_previous_version(self):
        path=Path(__file__).resolve().parents[1]/'history/v0.3.7/ultra/compression.py'
        spec=importlib.util.spec_from_file_location('previous_compression',path)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        rng=random.Random(782)
        for size in (0,1,17,4097,65537):
            data=rng.randbytes(size)
            for codec in codecs():
                for width in (1,2,4,8,16):
                    with self.subTest(size=size,codec=codec,width=width):
                        encoded=frame(data,codec,width)
                        self.assertEqual(encoded,old.frame(data,codec,width))
                        self.assertEqual(old.unframe(encoded),data)
                        self.assertEqual(unframe(old.frame(data,codec,width)),data)

    def test_reused_recipe_falls_back_on_whole_frame_size(self):
        # Un payload plus court d'un octet peut néanmoins donner une trame
        # plus longue : le nom du codec et les métadonnées comptent aussi.
        data=random.Random(42).randbytes(3001)
        encoder=AdaptiveEncoder(10)
        encoder.blocks=1;encoder.recipe=('zlib1',1)
        with patch('ultra.compression.compress',return_value=data[:-1]):
            encoded=encoder.encode(data)
        self.assertEqual(encoded,frame(data))
        self.assertEqual(unframe(encoded),data)
        self.assertEqual(encoder.recipe,('raw',1))

    def test_incompressible_reuse_and_source_unchanged(self):
        data=random.Random(78).randbytes(200003)
        before=hashlib.sha256(data).digest()
        encoder=AdaptiveEncoder(10,['raw'])
        for _ in range(3):
            encoded=encoder.encode(data)
            self.assertEqual(encoded,frame(data))
            self.assertEqual(unframe(encoded),data)
        self.assertEqual(hashlib.sha256(data).digest(),before)

    def test_fallback_frame_still_rejects_corruption(self):
        data=random.Random(81).randbytes(3001)
        encoder=AdaptiveEncoder(10)
        encoder.blocks=1;encoder.recipe=('zlib1',4)
        encoded=bytearray(encoder.encode(data))
        self.assertEqual(unframe(bytes(encoded)),data)
        encoded[-1]^=1
        with self.assertRaises(CodecError):unframe(bytes(encoded))
