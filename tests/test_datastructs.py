import unittest

from binascii import unhexlify

from examples.marketcoin import BitcoinHeader

class TestTransactions(unittest.TestCase):

    def setUp(self):
        pass

    def test_merkle_trees(self):
        # todo test MerkleLeavesToRoot
        # todo test MerkleBranchToRoot
        pass

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()