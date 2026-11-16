import hashlib
import random
import unittest
from unittest.mock import patch

from research.budget_compression import BudgetEncoder, RAW
from research.predictive_compression import frame, unframe, CodecError
from ultra.compression import MAX_BLOCK


class BudgetTests(unittest.TestCase):
    def test_fast_link_skips_codec_calls(self):
        with patch('research.budget_compression.compress',side_effect=AssertionError('unbudgeted codec')):
            e=BudgetEncoder(1e15)
            data=b'abcd'*65536
            self.assertEqual(unframe(e.encode(data)),data)
            self.assertEqual(e.recipe,RAW)
            self.assertEqual(e.last_search,[])

    def test_raw_only_and_arbitrary_lengths(self):
        e=BudgetEncoder(50,['raw'])
        rng=random.Random(123)
        for n in (0,1,3,1023,1024,4099,65537,MAX_BLOCK):
            d=rng.randbytes(n)
            self.assertEqual(unframe(e.encode(d)),d)
            self.assertEqual(e.recipe,RAW)

    def test_periodic_raw_reconsideration_is_bounded(self):
        e=BudgetEncoder(10,retune_every=3)
        with patch.object(e,'_select',side_effect=[RAW,('zlib1',1,'none')]):
            for _ in range(3):self.assertEqual(unframe(e.encode(b'x'*65536)),b'x'*65536)
            self.assertEqual(e.searches,1)
            self.assertEqual(unframe(e.encode(b'x'*65536)),b'x'*65536)
            self.assertEqual(e.searches,2)
            self.assertNotEqual(e.recipe,RAW)

    def test_change_to_noise_falls_back_and_never_expands(self):
        e=BudgetEncoder(10,['raw','zlib1'])
        data=b'hello'*30000
        self.assertEqual(unframe(e.encode(data)),data)
        noise=random.Random(109).randbytes(len(data))
        encoded=e.encode(noise)
        self.assertEqual(unframe(encoded),noise)
        self.assertEqual(e.recipe,RAW)
        self.assertLessEqual(len(encoded),len(frame(noise)))

    def test_no_unnegotiated_codec_and_oversize(self):
        e=BudgetEncoder(10,['raw','zlib1'])
        data=bytes(range(256))*4096+b'fin'
        self.assertEqual(unframe(e.encode(data)),data)
        self.assertNotIn(e.recipe[0],('zstd1','zstd3'))
        with self.assertRaises(CodecError):e.encode(b'0'*(MAX_BLOCK+1))

    def test_corruption_and_truncation_still_fail(self):
        data=b'abc'*100000
        encoded=BudgetEncoder(50).encode(data)
        bad=bytearray(encoded);bad[-1]^=1
        for damaged in (bytes(bad),encoded[:-1],encoded+b'extra'):
            with self.assertRaises((CodecError,ValueError)):unframe(damaged)


import test_predictive_research as previous


class BudgetHTTPS(unittest.TestCase):
    setUpClass=classmethod(previous.PredictiveHTTPSResearchTests.setUpClass.__func__)
    tearDownClass=classmethod(previous.PredictiveHTTPSResearchTests.tearDownClass.__func__)
    setUp=previous.PredictiveHTTPSResearchTests.setUp
    tearDown=previous.PredictiveHTTPSResearchTests.tearDown

    def test_budget_actual_tls_interrupt_resume_and_range(self):
        import threading
        from ultra.engine import Transfer,Options,digest
        from ultra.network import RemoteSource
        dest=self.base/'budget-received';stop=threading.Event()
        with patch('ultra.network.AdaptiveEncoder',side_effect=lambda *a,**kw:BudgetEncoder(50)), \
             patch('ultra.blockstream.unframe',unframe):
            remote=RemoteSource(self.url,self.token,self.cert,'ultra')
            first=Transfer(remote,dest,Options(workers=1,buffer_size=65536),cancel=stop,
                           progress=lambda n,t:stop.set() if n>=65536 else None).run()
            self.assertTrue(first.errors)
            result=Transfer(remote,dest,Options(workers=1)).run()
            self.assertFalse(result.errors,result.errors)
            self.assertGreater(result.resumed_bytes,0)
            self.assertEqual(digest(dest/'été.bin'),hashlib.sha256(self.data).hexdigest())
            self.assertTrue((dest/'dossier vide').is_dir())
            self.assertEqual((dest/'vide').read_bytes(),b'')
            e=next(e for e in remote.entries if e.path=='été.bin')
            with remote.open_range(e,19,100003) as stream:
                self.assertEqual(stream.read(100004),self.data[19:100022])
            remote.release_connections()
