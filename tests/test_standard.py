import unittest
import time
import sys

from cryptonet import Cryptonet
from cryptonet.datastructs import ChainVars
from cryptonet.chain import Chain
from cryptonet.statemaker import StateMaker
from cryptonet.standard import Tx
from cryptonet.dapp import TxPrism

class TestTransactions(unittest.TestCase):

    def setUp(self):
        self.state_maker = StateMaker(Chain(ChainVars()))
        self.state_maker.register_dapp(TxPrism(b'', self.state_maker))

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
            self.assertEqual(begin_state, self.state_maker.super_state[b''].complete_kvs())
            self.state_maker.super_state[b''][b'MAX'] = 15
            mid_state = {
                int.from_bytes(b'MAX', 'big'): 15
            }
            self.assertEqual(mid_state, self.state_maker.super_state[b''].complete_kvs())
            tx = Tx.make(dapp=b'',value=5,fee=0,data=[b'ANDI'])
            tx.sender = b'MAX'
            self.state_maker._process_tx(tx)
            end_state = {
                int.from_bytes(b'MAX', 'big'): 10,
                int.from_bytes(b'ANDI', 'big'): 5
            }
            self.assertEqual(end_state, self.state_maker.super_state[b''].complete_kvs())

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()