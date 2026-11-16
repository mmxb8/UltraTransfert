"""Complément existant : contrôles Python/Tcl réels, sans accès réseau."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import prepare_installation as setup
import test_installation as fixtures


def attach_dependencies(root):
    # Fixture explicitement liée au complément installé du banc, pas un installateur.
    import cryptography
    import _cffi_backend
    python = root/'.venv-run'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    result = subprocess.run([str(python), '-c', 'import sysconfig; print(sysconfig.get_path("purelib"))'],
                            capture_output=True, text=True, check=True)
    (Path(result.stdout.strip())/'test-existing-sharing.pth').write_text('\n'.join(dict.fromkeys((str(Path(cryptography.__file__).parent.parent), str(Path(_cffi_backend.__file__).parent))))+'\n')
    return python


class InstallationReuseTests(unittest.TestCase):
    def prepared(self, root):
        result = setup.prepare(root, offline=True)
        self.assertTrue(result['core_ready'])
        return attach_dependencies(root)

    def test_working_existing_dependency_skips_pip_and_preserves_core_probe(self):
        with fixtures.InstallationTests().project() as root:
            self.prepared(root); messages = []
            real = subprocess.run
            def run(args, **kw):
                self.assertNotIn('-m', args, 'Aucune installation attendue')
                return real(args, **kw)
            with patch('prepare_installation.subprocess.run', side_effect=run):
                report = setup.prepare(root, progress=messages.append)
            self.assertEqual(report['status'], 'ready')
            self.assertTrue(report['sharing_reused']); self.assertFalse(report['sharing_install_attempted'])
            self.assertGreater(report['core_probe']['resumed_bytes'], 0)
            self.assertIn('aucune installation', messages[-1])
            self.assertTrue(json.loads((root/'reports/installation.json').read_text())['sharing_reused'])

    def test_offline_also_reuses_verified_dependency(self):
        with fixtures.InstallationTests().project() as root:
            self.prepared(root)
            report = setup.prepare(root, offline=True)
            self.assertTrue(report['sharing_ready']); self.assertTrue(report['sharing_reused'])
            self.assertFalse(report['sharing_install_attempted'])

    def test_wrong_version_is_not_ready_offline(self):
        with fixtures.InstallationTests().project() as root:
            self.prepared(root)
            with patch.object(setup, 'SHARING_PROBE', "import cryptography; cryptography.__version__='0'; "+setup.SHARING_PROBE):
                report = setup.prepare(root, offline=True)
            self.assertTrue(report['core_ready']); self.assertFalse(report['sharing_ready'])
            self.assertFalse(report['sharing_reused']); self.assertFalse(report['sharing_install_attempted'])

    def test_wrong_version_attempts_install_but_network_failure_keeps_core(self):
        with fixtures.InstallationTests().project() as root:
            self.prepared(root); commands = []; real = subprocess.run
            def run(args, **kw):
                commands.append(args)
                if '-m' in args: return subprocess.CompletedProcess(args, 1, '', 'échec réseau simulé')
                return real(args, **kw)
            with patch.object(setup, 'SHARING_PROBE', "import cryptography; cryptography.__version__='0'; "+setup.SHARING_PROBE), patch('prepare_installation.subprocess.run', side_effect=run):
                report = setup.prepare(root)
            self.assertTrue(report['core_ready']); self.assertFalse(report['sharing_ready'])
            self.assertTrue(report['sharing_install_attempted']); self.assertFalse(report['sharing_reused'])
            self.assertTrue(any('ensurepip' in command for command in commands))

    def test_broken_dependency_does_not_skip_installation(self):
        with fixtures.InstallationTests().project() as root:
            self.prepared(root); real = subprocess.run
            def run(args, **kw):
                if '-m' in args: return subprocess.CompletedProcess(args, 1, '', 'pip indisponible simulé')
                return real(args, **kw)
            with patch.object(setup, 'SHARING_PROBE', "raise ImportError('complément inutilisable simulé')"), patch('prepare_installation.subprocess.run', side_effect=run):
                report = setup.prepare(root)
            self.assertTrue(report['core_ready']); self.assertFalse(report['sharing_reused'])
            self.assertTrue(report['sharing_install_attempted'])
