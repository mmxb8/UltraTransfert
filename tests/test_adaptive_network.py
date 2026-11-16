import os
import struct
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import test_network
from ultra.compression import MAX_BLOCK
from ultra.blockstream import MAGIC
from ultra.delta import DeltaSource
from ultra.engine import LocalSource, Options, Transfer, digest
from ultra.network import RemoteSource, make_server


class AdaptiveNetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_network.NetworkTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        test_network.NetworkTests.tearDownClass.__func__(cls)

    def setUp(self):
        self.case=tempfile.TemporaryDirectory(dir=self.root)
        self.base=Path(self.case.name)
        self.source=self.base/'source';self.source.mkdir()
        (self.source/'vide').mkdir()
        (self.source/'zéro').write_bytes(b'')
        unique=bytearray(bytes(range(256))*(MAX_BLOCK//128+3))
        for offset in range(0,len(unique)-4,65536):
            struct.pack_into('<I',unique,offset,offset//65536)
        self.data=bytes(unique)
        (self.source/'été.bin').write_bytes(self.data)
        self.token='experimental-'+'x'*48
        self.server=make_server(LocalSource(self.source),('127.0.0.1',0),self.cert,self.key,self.token,'ultra',65536,10,selection_pruning=True)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'https://localhost:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
        self.case.cleanup()

    def test_full_transfer_and_plain_client_fallback(self):
        for mode in ('ultra','none'):
            with self.subTest(mode=mode):
                destination=self.base/mode
                result=Transfer(RemoteSource(self.url,self.token,self.cert,mode),destination,Options(workers=1)).run()
                self.assertFalse(result.errors,result.errors)
                self.assertEqual(digest(destination/'été.bin'),digest(self.source/'été.bin'))
                self.assertTrue((destination/'vide').is_dir())
        self.assertGreater(self.server.transfer_metrics['recipe_reused_blocks'],0)
        self.assertGreater(self.server.transfer_metrics['block_wire_bytes'],0)

    def test_ranges_unaligned_offsets_and_delta(self):
        remote=RemoteSource(self.url,self.token,self.cert,'ultra')
        entry=next(e for e in remote.entries if e.path=='été.bin')
        with remote.open_range(entry,17,MAX_BLOCK+29) as stream:
            self.assertEqual(stream.read(MAX_BLOCK+30),self.data[17:17+MAX_BLOCK+29])
        reference=self.base/'reference';reference.mkdir()
        old=bytearray(self.data);old[65540]^=1
        (reference/'old').write_bytes(old)
        destination=self.base/'delta'
        origin=DeltaSource(remote,reference)
        result=Transfer(origin,destination,Options(workers=1)).run()
        self.assertFalse(result.errors,result.errors)
        self.assertEqual(origin.statistics()['downloaded_payload_bytes'],65536)
        self.assertEqual(digest(destination/'été.bin'),digest(self.source/'été.bin'))

    def test_cancel_and_resume_experimental_stream(self):
        remote=RemoteSource(self.url,self.token,self.cert,'ultra')
        cancel=threading.Event();destination=self.base/'resume'
        result=Transfer(remote,destination,Options(workers=1,buffer_size=65536,max_bytes_per_second=64e6),lambda n,total:cancel.set() if n>=65536 else None,cancel).run()
        self.assertTrue(result.errors)
        result=Transfer(remote,destination,Options(workers=1,buffer_size=65536,max_bytes_per_second=128e6)).run()
        self.assertFalse(result.errors,result.errors)
        self.assertGreater(result.resumed_bytes,0)

    def test_client_codec_negotiation(self):
        with patch('ultra.network.codecs',return_value=['raw','zlib1']):
            destination=self.base/'portable'
            remote=RemoteSource(self.url,self.token,self.cert,'ultra')
            result=Transfer(remote,destination,Options(workers=1)).run()
            self.assertFalse(result.errors,result.errors)

    def test_incomplete_stream_is_not_published(self):
        def incomplete(source,output,length,encoder,on_block):
            output.write(MAGIC)
            return len(MAGIC)
        with patch('ultra.network.write_stream',side_effect=incomplete):
            destination=self.base/'corrupt'
            result=Transfer(RemoteSource(self.url,self.token,self.cert,'ultra'),destination,Options(workers=1)).run()
        self.assertTrue(result.errors)
        self.assertFalse((destination/'été.bin').exists())
