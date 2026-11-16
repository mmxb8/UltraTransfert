import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from ultra.blockstream import write_stream, BlockReader
from ultra.predictive_budget import BudgetEncoder
from ultra.predictive_stream import LeanBlockReader, raw_view_unframe
from ultra.compression import CodecError
from ultra.validation import predictive_check, rdp_check, write_report
from ultra.network import RemoteStream, PREDICTIVE_ENCODING, RemoteSource
from ultra.engine import TransferError
import test_network


class PredictiveIntegrationTests(unittest.TestCase):
    def test_explicit_integrated_tls_resume_and_range_without_patches(self):
        result=predictive_check()
        self.assertTrue(result['sha256_verified'])
        self.assertGreater(result['resumed_bytes'],0)
        self.assertTrue(result['range_checked'])

    def test_stream_decoders_are_isolated(self):
        data=b'abcde'*20000
        a=io.BytesIO();write_stream(io.BytesIO(data),a,len(data),BudgetEncoder(50))
        b=io.BytesIO();write_stream(io.BytesIO(data),b,len(data))
        self.assertEqual(LeanBlockReader(io.BytesIO(a.getvalue()),len(data),decoder=raw_view_unframe).read(len(data)+1),data)
        self.assertEqual(BlockReader(io.BytesIO(b.getvalue()),len(data)).read(len(data)+1),data)
        with self.assertRaises(CodecError):
            BlockReader(io.BytesIO(a.getvalue()),len(data)).read(len(data)+1)

    def test_predictive_truncation_never_returns_final_bytes(self):
        data=b'protected'*1000
        out=io.BytesIO();write_stream(io.BytesIO(data),out,len(data),BudgetEncoder(50))
        for wire in (out.getvalue()[:-1],out.getvalue()+b'x'):
            reader=LeanBlockReader(io.BytesIO(wire),len(data),decoder=raw_view_unframe)
            target=bytearray(b'z'*len(data))
            with self.assertRaises(CodecError):reader.readinto(target)
            self.assertEqual(target, b'z'*len(data))

    def test_rdp_refuses_simulation_without_modifying_parents(self):
        with tempfile.TemporaryDirectory() as temp, patch('ultra.validation.native_windows',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'Windows'):
                rdp_check(temp,temp)
            self.assertEqual(list(Path(temp).iterdir()),[])
            report=Path(temp)/'report.json'
            self.assertEqual(write_report('rdp',report,temp,temp),1)
            self.assertIn('"status": "failed"',report.read_text())


class NegotiationTests(unittest.TestCase):
    setUpClass=classmethod(test_network.NetworkTests.setUpClass.__func__)
    tearDownClass=classmethod(test_network.NetworkTests.tearDownClass.__func__)
    setUp=test_network.NetworkTests.setUp
    tearDown=test_network.NetworkTests.tearDown

    def test_predictive_client_refuses_legacy_server(self):
        remote=RemoteSource(self.url,self.token,self.cert,'predictive')
        try:
            entry=next(e for e in remote.entries if e.kind=='file')
            with self.assertRaisesRegex(TransferError,'non négociée'):
                remote.open(entry)
        finally:
            remote.release_connections()
