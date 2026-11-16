"""Parties portables testées sous l'hôte courant ; aucun faux essai Windows."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from build_windows import bundle_zip, validate_smoke
from ultra import __version__
from ultra.smoke import check, write_report


class PortableTests(unittest.TestCase):
    def test_embedded_copy_and_resume_without_display(self):
        result = check(require_gui=False)
        self.assertEqual(result['status'], 'passed')
        self.assertGreater(result['resumed_bytes'], 0)
        self.assertEqual(result['files'], 3)
        self.assertFalse(result['gui_created'])
        self.assertFalse(result['frozen'])
        with self.assertRaises(RuntimeError):
            validate_smoke(result)  # Linux and source runs never qualify as Windows.

    def test_report_failure_is_nonzero(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)/'erreur.json'
            with patch('ultra.smoke.check', side_effect=RuntimeError('Tk indisponible')):
                self.assertEqual(write_report(report), 1)
            self.assertEqual(json.loads(report.read_text())['status'], 'failed')

    def test_report_success(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp)/'succès.json'
            self.assertEqual(write_report(report, require_gui=False), 0)
            self.assertEqual(json.loads(report.read_text())['version'], __version__)

    def test_archive_keeps_support_files_with_spaces_unicode(self):
        # Fixtures are not real executable binaries and are never presented as such.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'build été'; root.mkdir()
            (root/'UltraTransfert.exe').write_bytes(b'fixture-not-an-executable')
            (root/'_internal').mkdir()
            (root/'_internal'/'données.dll').write_bytes(b'fixture-dependency')
            output = Path(temp)/'candidate.zip'
            bundle_zip(root, output)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                extracted = Path(temp)/'extrait espaces 日本語'
                archive.extractall(extracted)
            self.assertEqual((extracted/'UltraTransfert/_internal/données.dll').read_bytes(), b'fixture-dependency')
            self.assertEqual((extracted/'UltraTransfert/UltraTransfert.exe').read_bytes(), b'fixture-not-an-executable')

    def test_missing_exe_never_creates_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'absent.zip'
            with self.assertRaises(RuntimeError):
                bundle_zip(temp, output)
            self.assertFalse(output.exists())

    def test_linked_dependency_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'bundle'; root.mkdir()
            (root/'UltraTransfert.exe').write_bytes(b'fixture')
            (root/'link').symlink_to(root/'UltraTransfert.exe')
            with self.assertRaises(RuntimeError):
                bundle_zip(root, Path(temp)/'refused.zip')

    def test_windows_validation_guard(self):
        report = dict(status='passed', version=__version__, platform='win32', frozen=True,
                      gui_created=True, sharing_prepared=True, sharing_session_checked=True, sharing_restore_checked=True, resumed_bytes=1)
        validate_smoke(report)  # Validation schema only, not an executed Windows test.
        for key, bad in [('status', 'failed'), ('version', 'old'), ('platform', 'linux'),
                         ('frozen', False), ('gui_created', False), ('sharing_prepared', False), ('sharing_session_checked', False), ('sharing_restore_checked', False), ('resumed_bytes', 0)]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_smoke({**report, key: bad})

    @unittest.skipIf(sys.platform == 'win32', 'Guard is for non-Windows hosts')
    def test_non_windows_build_refused_before_building(self):
        proc = subprocess.run([sys.executable, 'build_windows.py'], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('Construction Windows uniquement', proc.stderr)
