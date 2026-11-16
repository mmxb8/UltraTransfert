import concurrent.futures
import http.client
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import test_network
from ultra.engine import Transfer, Options, digest
from ultra.network import RemoteSource, ChunkedWriter
from ultra.https_pool import HTTPSPool, Response


class ReuseTests(unittest.TestCase):
    setUpClass = classmethod(test_network.NetworkTests.setUpClass.__func__)
    tearDownClass = classmethod(test_network.NetworkTests.tearDownClass.__func__)
    setUp = test_network.NetworkTests.setUp
    tearDown = test_network.NetworkTests.tearDown
    def counted(self):
        self.accepted = 0
        original = self.server.get_request
        def get_request():
            result = original()
            self.accepted += 1
            return result
        self.server.get_request = get_request
        return RemoteSource(self.url, self.token, self.cert)

    def test_single_connection_all_requests(self):
        remote = self.counted()
        result = Transfer(remote, Path(self.case.name)/'reuse', Options(workers=1)).run()
        self.assertFalse(result.errors, result.errors)
        self.assertEqual(self.accepted, 1)
        self.assertEqual(remote.pool.idle, [])

    def test_compressed_connection_reuse(self):
        for compression in ("auto", "gzip"):
            with self.subTest(compression=compression):
                remote = RemoteSource(self.url, self.token, self.cert, compression)
                remote.get_manifest()
                connection = remote.pool.idle[0]
                entry = next(e for e in remote.entries if e.kind == "file" and e.size)
                # Une plage bornée conserve le même framing que les petits fichiers.
                with remote.open_range(entry, 0, 1024) as stream:
                    self.assertEqual(stream.read(1025), (self.source/entry.path).read_bytes()[:1024])
                self.assertIs(remote.pool.idle[0], connection)
                remote.release_connections()

    def test_partial_read_is_discarded(self):
        remote = self.counted()
        entry = next(e for e in remote.entries if e.kind == 'file' and e.size)
        with remote.open(entry) as stream:
            self.assertEqual(len(stream.read(1)), 1)
        self.assertEqual(remote.pool.idle, [])
        with remote.open(entry) as stream:
            self.assertEqual(len(stream.read(entry.size+1)), entry.size)
        self.assertEqual(self.accepted, 2)
        remote.release_connections()

    def test_parallel_contents_are_isolated(self):
        remote = self.counted()
        files = [e for e in remote.entries if e.kind == 'file']*10
        def read(entry):
            with remote.open(entry) as stream:
                return entry, stream.read(entry.size+1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for entry, data in pool.map(read, files):
                self.assertEqual(data, (self.source/entry.path).read_bytes())
        self.assertLessEqual(self.accepted, 4)
        remote.release_connections()

    def test_http10_peer_keeps_working_without_reuse(self):
        self.server.RequestHandlerClass.protocol_version = 'HTTP/1.0'
        remote = self.counted()
        result = Transfer(remote, Path(self.case.name)/'old', Options(workers=1)).run()
        self.assertFalse(result.errors, result.errors)
        self.assertGreater(self.accepted, 1)

    def test_interrupt_and_resume_raw(self):
        import threading
        remote = self.counted(); stop = threading.Event()
        dest = Path(self.case.name)/'resume'
        first = Transfer(remote, dest, Options(workers=1, buffer_size=65536),
                         cancel=stop, progress=lambda n,total: stop.set() if n >= 65536 else None).run()
        self.assertTrue(first.errors)
        self.assertEqual(remote.pool.idle, [])
        second = Transfer(remote, dest, Options(workers=1, buffer_size=65536)).run()
        self.assertFalse(second.errors, second.errors)
        self.assertGreater(second.resumed_bytes, 0)
        for entry in remote.entries:
            if entry.kind == 'file': self.assertEqual(digest(dest/entry.path), entry.sha256)

    def test_broken_idle_connection_is_not_retried_silently(self):
        import socket
        from urllib.error import URLError
        remote = self.counted()
        with self.server._connections_lock:
            sockets = list(self.server._connections)
        for sock in sockets:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        with self.assertRaises((URLError, http.client.HTTPException)):
            remote.get_manifest()
        self.assertEqual(remote.pool.idle, [])
        self.assertEqual(remote.get_manifest(), remote.payload)
        remote.release_connections()

    def test_prepare_error_releases_idle_connections(self):
        remote = self.counted()
        dest = Path(self.case.name)/'locked'; dest.mkdir()
        state = dest/'.ultratransfert-state'; state.mkdir(); (state/'manifest.json').write_text('{}')
        (state/'lock').write_text('active')
        with self.assertRaises(Exception): Transfer(remote, dest).run()
        self.assertEqual(remote.pool.idle, [])
        self.assertTrue((state/'lock').exists())


class PoolUnitTests(unittest.TestCase):
    def test_chunked_writer_roundtrip_and_bounds(self):
        import io
        payload = bytes(range(256))*1025
        output = io.BytesIO(); writer = ChunkedWriter(output)
        self.assertEqual(writer.write(payload), len(payload))
        self.assertEqual(writer.write(b''), 0)
        writer.finish()
        wire = io.BytesIO(output.getvalue()); reconstructed = bytearray()
        while True:
            size = int(wire.readline(), 16)
            self.assertLessEqual(size, 65536)
            if not size:
                self.assertEqual(wire.read(), b'\r\n')
                break
            reconstructed.extend(wire.read(size))
            self.assertEqual(wire.read(2), b'\r\n')
        self.assertEqual(bytes(reconstructed), payload)

    def test_invalid_port_has_no_cleanup_error(self):
        import sys
        from unittest.mock import patch
        with patch.object(sys, "unraisablehook") as errors:
            with self.assertRaises(ValueError): HTTPSPool("https://localhost:invalid", None)
        errors.assert_not_called()

    def test_idle_bound_and_cleanup(self):
        pool = HTTPSPool('https://localhost', None, max_idle=2)
        connections = [Mock() for _ in range(3)]
        for c in connections: pool.release(c, True)
        self.assertEqual(len(pool.idle), 2)
        connections[2].close.assert_called_once()
        pool.close(); pool.close()
        for c in connections: c.close.assert_called_once()

    def test_incomplete_or_close_delimited_never_reused(self):
        for length, will_close in ((1,False),(None,True),(0,True)):
            pool, conn, raw = Mock(), Mock(), Mock(length=length,will_close=will_close,chunked=False)
            response = Response(pool, conn, raw)
            response.close(); response.close()
            pool.release.assert_called_once_with(conn, False)

    def test_truncation_is_propagated_and_discarded(self):
        pool, conn = Mock(), Mock()
        raw = Mock(length=8,will_close=False)
        raw.read.side_effect = http.client.IncompleteRead(b'bad',8)
        with self.assertRaises(http.client.IncompleteRead):
            with Response(pool,conn,raw) as response: response.read()
        pool.release.assert_called_once_with(conn,False)
