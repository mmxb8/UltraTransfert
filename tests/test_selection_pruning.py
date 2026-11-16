"""Bornes du modèle sous horloge contrôlée, aucune assertion de vitesse machine."""
import random
import unittest
from unittest.mock import patch

from ultra import compression as c


class SelectionPruningTests(unittest.TestCase):
    def profile(self,data,encoding_cost,corrupt=False):
        now=[0.0];encode=c.frame;decode=c.unframe
        def frame(sample,codec,width):
            encoded=encode(sample,codec,width)
            now[0]+=encoding_cost(codec,width)
            if corrupt and codec=='zlib1' and width==1:
                encoded=encoded[:-1]+bytes([encoded[-1]^1])
            return encoded
        def unframe(encoded):
            now[0]+=.001
            return decode(encoded)
        with patch('ultra.compression.time.perf_counter',side_effect=lambda:now[0]),patch('ultra.compression.frame',side_effect=frame),patch('ultra.compression.unframe',side_effect=unframe):
            return c.adaptive_frame(data,1e6,['raw','zlib1'],prune=True)

    def test_slow_candidates_cannot_replace_verified_raw(self):
        data=random.Random(8).randbytes(17000)
        encoded,details=self.profile(data,lambda codec,width:.001 if codec=='raw' else .003)
        self.assertEqual(details['selected']['codec'],'raw')
        self.assertEqual(sum(bool(x.get('pruned')) for x in details['candidates']),5)
        self.assertEqual(c.unframe(encoded),data)
        best=details['selected']['estimated_seconds']
        self.assertTrue(all(x['estimated_seconds']>=best for x in details['candidates'] if x.get('pruned')))

    def test_potentially_better_candidate_is_decoded(self):
        data=b'abc123'*3000
        encoded,details=self.profile(data,lambda codec,width:.0001 if (codec,width)==('zlib1',1) else .003)
        self.assertEqual((details['selected']['codec'],details['selected']['width']),('zlib1',1))
        self.assertFalse(details['selected'].get('pruned',False))
        self.assertEqual(c.unframe(encoded),data)

    def test_corrupt_potential_winner_is_rejected(self):
        with self.assertRaises(c.CodecError):
            self.profile(b'abcd'*4000,lambda codec,width:.0001 if codec=='zlib1' else .003,corrupt=True)

    def test_roundtrip_limits_and_unpruned_selection_across_negotiation(self):
        inputs=[b'',b'a',random.Random(1).randbytes(65537),bytes(range(256))*500]
        for allowed in (['raw'],['raw','zlib1'],c.codecs()):
            for data in inputs:
                for rate in (1e-320,1e-300,1,50,10000,1e308):
                    with self.subTest(allowed=allowed,size=len(data),rate=rate):
                        encoded,details=c.adaptive_frame(data,rate,allowed,prune=True)
                        self.assertFalse(details['selected'].get('pruned',False))
                        self.assertLessEqual(len(encoded),len(c.frame(data)))
                        self.assertEqual(c.unframe(encoded),data)

    def test_pruning_disabled_by_default(self):
        data=b'abcd'*4000
        encoded,details=c.adaptive_frame(data)
        self.assertTrue(all(not x.get('pruned') for x in details['candidates']))
        self.assertFalse(c.AdaptiveEncoder().prune)
        self.assertEqual(c.unframe(encoded),data)

    def test_server_option_rejected_outside_ultra(self):
        from ultra.network import make_server
        from ultra.engine import TransferError
        with self.assertRaisesRegex(TransferError,'compression ultra'):
            make_server(None,('127.0.0.1',0),'absent','absent','x'*48,selection_pruning=True)
