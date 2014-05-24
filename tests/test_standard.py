import unittest
import time
import sys

from cryptonet import Cryptonet
from cryptonet.datastructs import ChainVars
from cryptonet.chain import Chain
from cryptonet.statemaker import StateMaker

class TestTransactions(unittest.TestCase):

    def setUp(self):
        chainvars = ChainVars()
        self.cryptonet = Cryptonet(chainvars)
        self.state_maker = self.cryptonet.chain.head.state_maker
        self.cryptonet.run()

    def test_mine_genesis(self):
        pass

    def test_mine(self):
        pass

    def test_blocks(self):
        pass

    def test_invalid_blocks(self):
        pass

    def test_headers(self):
        pass

    def test_invalid_headers(self):
        pass

    def test_transactions_unsigned(self):
        ''' Create some unsigned transactions (temp) that will be applied to state.
        The state should alter itself accordingly.
        '''
        with self.state_maker.trial_state():
            begin_state = {}

            mid_state = {
                b'MAX': 15
            }

            end_state = {
                b'MAX': 10,
                b'ANDI': 5
            }
            self.assertEqual(end_state, self.state_maker.super_state[b''].)

    def tearDown(self):
        self.cryptonet.shutdown()

if __name__ == '__main__':
    unittest.main()