import unittest

from cryptonet import Cryptonet
from examples.minblock import MinBlock

class TestTransactions(unittest.TestCase):
    def setUp(self):
        self.cryptonet = Cryptonet(seeds=[], address='0.0.0.0:5003', block_class=MinBlock, mine=True, enable_p2p=False)

    def test_genesis_mines_spontaneously(self):
        self.cryptonet.genesis.assert_validity(self.cryptonet.chain)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()