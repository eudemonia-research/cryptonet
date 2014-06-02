import unittest

from binascii import unhexlify

from examples.marketcoin import BitcoinHeader

class TestTransactions(unittest.TestCase):

    def setUp(self):
        pass

    def test_bitcoin_headers(self):
        genesis_header = BitcoinHeader.make_from_bytes(unhexlify("0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c"))
        genesis_header.assert_internal_consistency()

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()