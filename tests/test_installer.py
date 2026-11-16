import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from build_installer import extract_zip, fetch_inputs, generate_uninstall
from ultra.install_integrity import verify_payload


class InstallerTests(unittest.TestCase):
    def fixture(self, base):
        root = Path(base)/'app'
        root.mkdir()
        (root/'données été.txt').write_bytes(b'expected')
        (root/'payload-manifest.json').write_text(json.dumps({'files':{
            'données été.txt':hashlib.sha256(b'expected').hexdigest()}}))
        return root

    def test_verified_payload_then_corruption_and_missing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(temp)
            self.assertEqual(verify_payload(root), 1)
            (root/'données été.txt').write_bytes(b'corrupted')
            with self.assertRaises(ValueError): verify_payload(root)
            (root/'données été.txt').unlink()
            with self.assertRaises(OSError): verify_payload(root)

    def test_manifest_cannot_read_outside_installation(self):
        for name in ['../private', '/private', 'C:/private', 'a\\private']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = self.fixture(temp)
                (root/'payload-manifest.json').write_text(json.dumps({'files':{name:'0'*64}}))
                with self.assertRaises(ValueError): verify_payload(root)

    def test_link_to_matching_external_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(temp)
            external = Path(temp)/'outside'
            external.write_bytes(b'expected')
            (root/'données été.txt').unlink()
            (root/'données été.txt').symlink_to(external)
            with self.assertRaises(ValueError): verify_payload(root)

    def test_zip_path_traversal_is_rejected_before_any_extraction(self):
        for name in ['../escape', '/escape', 'C:/escape', 'nested\\escape']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                archive = Path(temp)/'input.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    z.writestr('valid.txt', b'content')
                    z.writestr(name,b'bad')
                output = Path(temp)/'output'
                with self.assertRaises(ValueError): extract_zip(archive,output)
                self.assertFalse(output.exists())

    def test_zip_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp)/'link.zip'
            with zipfile.ZipFile(archive,'w') as z:
                info=zipfile.ZipInfo('link'); info.create_system=3
                info.external_attr=(0o120777 << 16)
                z.writestr(info,b'../outside')
            with self.assertRaises(ValueError): extract_zip(archive,Path(temp)/'out')

    def test_uninstall_is_a_fixed_list_with_escaped_filenames(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'dossier').mkdir()
            (root/'dossier'/'été$1.txt').touch()
            script=generate_uninstall(root)
            self.assertIn('été$$1.txt',script)
            self.assertNotIn('RMDir /r',script)
            self.assertNotIn('*',script)
            self.assertNotIn('unrelated.txt',script)

    def test_offline_input_failure_never_uses_network(self):
        with tempfile.TemporaryDirectory() as temp, patch('urllib.request.urlopen') as request:
            with self.assertRaises(FileNotFoundError): fetch_inputs(temp,offline=True)
            request.assert_not_called()

    def test_input_with_wrong_hash_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as temp, patch('urllib.request.urlopen') as request:
            (Path(temp)/'python-3.14.10-embed-amd64.zip').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'Empreinte'): fetch_inputs(temp,offline=True)
            request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
