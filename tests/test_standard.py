import unittest
import time
import sys

from binascii import unhexlify

from cryptonet import Cryptonet
from cryptonet.chain import Chain
from cryptonet.statemaker import StateMaker
from cryptonet.standard import Tx, SuperTx, Point
from cryptonet.dapp import TxPrism
from cryptonet.errors import ValidationError

import encodium

from pycoin import ecdsa

pubkey = Point(x=55066263022277343669578718895168534326250603453777594175500187360389116729240,
               y=32670510020758816978083085130507043184471273380659243275938904335757337482424)

secret_exponent = 0x1

class TestTransactions(unittest.TestCase):

    def setUp(self):
        self.state_maker = StateMaker(Chain())
        self.state_maker.register_dapp(TxPrism(b'', self.state_maker))

        class FakeBlock:
            def __init__(self): self.height = 1
        self.fake_block = FakeBlock()

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
            for key in mid_state.keys():
                self.assertEqual(mid_state[key], self.state_maker.super_state[b''].complete_kvs()[key])
            self.assertEqual(mid_state, self.state_maker.super_state[b''].complete_kvs())
            tx = Tx(dapp=b'',value=5,fee=0,data=[b'ANDY'])
            tx.sender = int.from_bytes(b'MAX', 'big')
            self.state_maker._process_tx(tx)
            end_state = {
                int.from_bytes(b'MAX', 'big'): 10,
                int.from_bytes(b'ANDY', 'big'): 5
            }
            for key in end_state.keys():
                self.assertEqual(end_state[key], self.state_maker.super_state[b''].complete_kvs()[key])

    def test_super_transactions(self):
        ''' This WILL fail once signatures start working. Will need to be re-written.
        The signature will need to be calculated and hardcoded for a pubkey (or randomly generated).
        '''
        with self.state_maker.trial_state():
            begin_state = {}
            self.assertEqual(begin_state, self.state_maker.super_state[b''].complete_kvs())
            self.state_maker.super_state[b''][b'MAX'] = 15
            mid_state = {
                int.from_bytes(b'MAX', 'big'): 15
            }
            for key in mid_state.keys():
                self.assertEqual(mid_state[key], self.state_maker.super_state[b''].complete_kvs()[key])

            tx = Tx(dapp=b'',value=5,fee=0,data=[b'ANDY'])
            super_tx = SuperTx(txs=[tx], sender=pubkey)
            super_tx = super_tx.sign(secret_exponent)
            super_tx.assert_internal_consistency()
            tx.sender = int.from_bytes(b'MAX', 'big')
            self.state_maker.most_recent_block = self.fake_block
            self.state_maker._add_super_txs([super_tx])
            end_state = {
                int.from_bytes(b'MAX', 'big'): 10,
                int.from_bytes(b'ANDY', 'big'): 5
            }
            for key in end_state.keys():
                self.assertEqual(end_state[key], self.state_maker.super_state[b''].complete_kvs()[key])
            tx1 = Tx(dapp=b'', value=3, fee=0, data=[b'ANDY'])
            tx2 = Tx(dapp=b'', value=5, fee=0, data=[b'MAX'])
            super_tx = SuperTx(txs=[tx1, tx2], sender=pubkey)
            super_tx = super_tx.sign(secret_exponent)
            tx1.sender = int.from_bytes(b'MAX', 'big')
            tx2.sender = int.from_bytes(b'ANDY', 'big')
            super_tx.assert_internal_consistency()
            self.state_maker._add_super_txs([super_tx])
            real_end_state = {
                int.from_bytes(b'MAX', 'big'): 12,
                int.from_bytes(b'ANDY', 'big'): 3,
            }
            for key in end_state.keys():
                self.assertEqual(real_end_state[key], self.state_maker.super_state[b''].complete_kvs()[key])


    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
