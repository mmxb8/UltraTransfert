import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from ultra.engine import Entry, LocalSource, Options, STATE, Transfer, TransferError, digest, inventory, validate_entries


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.src = self.root/"source"
        self.src.mkdir()
        self.dst = self.root/"destination"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data=b"abc"):
        p = self.src/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def run_copy(self, options=None, **kwargs):
        return Transfer(LocalSource(self.src), self.dst, options or Options(buffer_size=65536), **kwargs).run()

    def test_mixed_tree_and_metadata(self):
        self.write(".cache/été_العربية_日本語.bin", os.urandom(210001))
        self.write("vide", b"")
        self.write("compressible", b"a"*150000)
        (self.src/"dossier vide").mkdir()
        os.utime(self.src/"vide", ns=(1600000000000000000, 1600000000000000000))
        r = self.run_copy()
        self.assertEqual(r.errors, [])
        self.assertEqual((r.files, r.directories), (3, 2))
        for e in inventory(self.src):
            if e.kind == "file":
                self.assertEqual(digest(self.src/e.path), digest(self.dst/e.path))
                self.assertEqual((self.dst/e.path).stat().st_mtime_ns, e.mtime_ns)
        self.assertTrue((self.dst/"dossier vide").is_dir())

    def test_windows_inventory_uses_authoritative_file_identity(self):
        path = self.write('.cache', b'original')
        class CachedEntry:
            name = path.name
            def __init__(self):
                self.path = str(path)
            def stat(self, **kwargs):
                raise AssertionError('Do not use incomplete Windows DirEntry metadata')
        class Scan:
            def __enter__(self):
                return iter([CachedEntry()])
            def __exit__(self, *args):
                return False
        with patch('ultra.engine.sys.platform', 'win32'), patch('ultra.engine.os.scandir', return_value=Scan()):
            source = LocalSource(self.src)
        entry = source.entries[0]
        self.assertEqual(entry.identity[2:4], (path.lstat().st_dev, path.lstat().st_ino))
        source.check(entry)
        with source.open(entry) as stream:
            self.assertEqual(stream.read(), b'original')
        path.write_bytes(b'changed size')
        with self.assertRaises(TransferError):
            source.check(entry)

    def test_many_small_files(self):
        for i in range(250):
            self.write(f"d{i%7}/f{i}", str(i).encode()*10)
        r = self.run_copy()
        self.assertFalse(r.errors)
        self.assertEqual(r.files, 250)

    def test_empty_source(self):
        r = self.run_copy()
        self.assertFalse(r.errors)
        self.assertEqual(r.bytes, 0)

    def test_identical_existing_is_verified(self):
        self.write("a")
        self.dst.mkdir()
        (self.dst/"a").write_bytes(b"abc")
        r = self.run_copy()
        self.assertFalse(r.errors)
        self.assertEqual(r.reused, 1)

    def test_conflict_does_not_overwrite(self):
        self.write("a")
        self.dst.mkdir()
        (self.dst/"a").write_bytes(b"bad")
        r = self.run_copy()
        self.assertTrue(r.errors)
        self.assertEqual((self.dst/"a").read_bytes(), b"bad")
        self.assertEqual((self.src/"a").read_bytes(), b"abc")

    def test_extra_destination_is_error(self):
        self.dst.mkdir()
        (self.dst/"extra").write_bytes(b"x")
        self.assertTrue(self.run_copy().errors)

    def test_overlap_is_rejected(self):
        with self.assertRaises(TransferError):
            Transfer(LocalSource(self.src), self.src/"inside")

    def test_source_symlink_rejected(self):
        self.write("a")
        try:
            (self.src/"link").symlink_to(self.src/"a")
        except OSError:
            self.skipTest("Symlinks indisponibles")
        with self.assertRaises(TransferError):
            LocalSource(self.src)

    def test_destination_symlink_rejected(self):
        self.write("a")
        self.dst.mkdir()
        (self.dst/"a").symlink_to(self.src/"a")
        self.assertTrue(self.run_copy().errors)

    def test_case_and_unicode_collisions(self):
        for names in (("A", "a"), ("é", "e\u0301")):
            with self.subTest(names=names):
                entries = [Entry(n, "file", 0, 0, 0o600) for n in names]
                with self.assertRaises(TransferError):
                    validate_entries(entries)

    def test_path_attacks_and_reserved_names(self):
        for p in ("../outside", "/etc/passwd", "a\\b", "C:x", STATE+"/x", "CON", "a.", "a//b", "a\x00b"):
            with self.subTest(p=p), self.assertRaises(TransferError):
                validate_entries([Entry(p, "file", 0, 0, 0o600)])

    def test_source_mutation_is_error(self):
        self.write("large", b"a"*200000)
        mutated = [False]
        def progress(n, total):
            if n and not mutated[0]:
                mutated[0] = True
                (self.src/"large").write_bytes(b"b"*200000)
        self.assertTrue(self.run_copy(progress=progress).errors)
        self.assertFalse((self.dst/"large").exists())

    def test_added_source_file_is_error(self):
        self.write("a", b"a"*100000)
        def progress(n, total):
            if n:
                self.write("new")
        self.assertTrue(self.run_copy(progress=progress).errors)

    def test_interrupt_then_resume(self):
        data = os.urandom(700000)
        self.write("large", data)
        event = threading.Event()
        def progress(n, total):
            if n >= 131072:
                event.set()
        r = self.run_copy(progress=progress, cancel=event)
        self.assertTrue(r.errors)
        self.assertFalse((self.dst/"large").exists())
        resumed = self.run_copy()
        self.assertFalse(resumed.errors)
        self.assertGreaterEqual(resumed.resumed_bytes, 131072)
        self.assertEqual((self.dst/"large").read_bytes(), data)

    def partial(self, data):
        transfer = Transfer(LocalSource(self.src), self.dst, Options(buffer_size=65536))
        transfer.prepare()
        (transfer.state/"lock").unlink()
        key = hashlib.sha256(b"large").hexdigest()+".part"
        p = transfer.state/"parts"/key
        p.write_bytes(data)
        return p

    def test_corrupted_partial_is_repaired(self):
        data = os.urandom(300000)
        self.write("large", data)
        self.partial(data[:65536]+b"X"*65536)
        r = self.run_copy()
        self.assertFalse(r.errors)
        self.assertEqual(r.resumed_bytes, 65536)
        self.assertEqual((self.dst/"large").read_bytes(), data)

    def test_oversized_partial_is_truncated(self):
        self.write("large", b"hello")
        self.partial(b"helloEXTRA")
        self.assertFalse(self.run_copy().errors)
        self.assertEqual((self.dst/"large").read_bytes(), b"hello")

    def test_wrong_manifest_rejected(self):
        self.write("large")
        self.partial(b"")
        self.write("new")
        with self.assertRaises(TransferError):
            self.run_copy()

    def test_lock_refuses_second_writer(self):
        t = Transfer(LocalSource(self.src), self.dst)
        t.prepare()
        try:
            with self.assertRaises(TransferError):
                self.run_copy()
        finally:
            (t.state/"lock").unlink()

    def test_final_corruption_detected(self):
        self.write("a", b"123456")
        from ultra import engine
        original = engine.install_no_replace
        def corrupt(src, dst):
            original(src, dst)
            Path(dst).write_bytes(b"654321")
        with patch("ultra.engine.install_no_replace", corrupt):
            self.assertTrue(self.run_copy().errors)

    def test_install_race_does_not_overwrite(self):
        self.write("a")
        from ultra import engine
        original = engine.install_no_replace
        def race(src, dst):
            Path(dst).write_bytes(b"other writer")
            original(src, dst)
        with patch("ultra.engine.install_no_replace", race):
            self.assertTrue(self.run_copy().errors)
        self.assertEqual((self.dst/"a").read_bytes(), b"other writer")

    def test_native_full_and_resume(self):
        native = Path(__file__).resolve().parents[1]/"bin"/("ultra_native.exe" if os.name == "nt" else "ultra_native")
        if not native.exists():
            self.skipTest("Helper absent")
        data = os.urandom(600000)
        self.write("large", data)
        self.partial(data[:65536])
        r = self.run_copy(Options(buffer_size=65536, native=str(native), native_threshold=0))
        self.assertFalse(r.errors)
        self.assertEqual(r.resumed_bytes, 65536)
        self.assertEqual((self.dst/"large").read_bytes(), data)

    def test_insufficient_space_releases_lock(self):
        from collections import namedtuple
        self.write("large", b"x"*1000)
        usage = namedtuple("usage", "total used free")(100, 99, 1)
        with patch("ultra.engine.shutil.disk_usage", return_value=usage):
            with self.assertRaisesRegex(TransferError, "Espace insuffisant"):
                self.run_copy()
        self.assertFalse((self.dst/STATE/"lock").exists())
        self.assertFalse(self.run_copy().errors)

    def test_cancel_during_final_hash_preserves_resumability(self):
        self.write("large", os.urandom(200000))
        event = threading.Event()
        def phase(message):
            if message.startswith("Vérification finale"):
                event.set()
        result = self.run_copy(cancel=event, phase=phase)
        self.assertTrue(result.errors)
        self.assertFalse((self.dst/STATE/"lock").exists())
        self.assertFalse(self.run_copy().errors)

    def test_report_failure_releases_lock(self):
        self.write("a")
        original = Path.write_text
        def fail(path, *args, **kwargs):
            if path.name == "last-result.json":
                raise OSError("simulated disk failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "write_text", fail):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.run_copy()
        self.assertFalse((self.dst/STATE/"lock").exists())
        self.assertFalse(self.run_copy().errors)

    def test_parallel_and_serial_have_identical_hashes(self):
        for i in range(15):
            self.write(f"dir/{i}", os.urandom(13001+i))
        first = self.run_copy(Options(workers=1, buffer_size=65536))
        other = Transfer(LocalSource(self.src), self.root/"parallel",
                         Options(workers=4, buffer_size=65536)).run()
        self.assertEqual(first.errors + other.errors, [])
        self.assertEqual(first.hashes, other.hashes)


if __name__ == "__main__":
    unittest.main()
