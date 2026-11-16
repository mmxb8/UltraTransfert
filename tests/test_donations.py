import hashlib
import json
from pathlib import Path
import unittest

from ultra.donations import BITCOIN_ADDRESS, BITCOIN_URI, QR_PATH, valid_bitcoin_address


class DonationTests(unittest.TestCase):
    def test_exact_requested_address_and_uri(self):
        self.assertEqual(BITCOIN_ADDRESS, '3HaGinyFJQJXFAMgU8SBuDxdS5aG5BQUNU')
        self.assertEqual(BITCOIN_URI, 'bitcoin:3HaGinyFJQJXFAMgU8SBuDxdS5aG5BQUNU')
        self.assertTrue(valid_bitcoin_address(BITCOIN_ADDRESS))

    def test_corrupted_addresses_are_rejected(self):
        for address in [None, '', BITCOIN_ADDRESS[:-1]+'1', '0'+BITCOIN_ADDRESS[1:],
                        BITCOIN_ADDRESS+'?amount=1', '1'*34, 'a'*100000]:
            with self.subTest(address=str(address)[:50]):
                self.assertFalse(valid_bitcoin_address(address))

    def test_assets_match_verified_manifest(self):
        manifest = json.loads(QR_PATH.with_name('bitcoin-donation.json').read_text())
        self.assertEqual(manifest['payload'], BITCOIN_URI)
        for name, expected in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((QR_PATH.parent/name).read_bytes()).hexdigest(), expected)
        self.assertTrue(QR_PATH.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))


if __name__ == '__main__':
    unittest.main()
