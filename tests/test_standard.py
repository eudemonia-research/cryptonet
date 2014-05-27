import unittest
import time
import sys

from binascii import unhexlify

from cryptonet import Cryptonet
from cryptonet.datastructs import ChainVars
from cryptonet.chain import Chain
from cryptonet.statemaker import StateMaker
from cryptonet.standard import Tx, SuperTx, Signature
from cryptonet.dapp import TxPrism
from cryptonet.errors import ValidationError

import encodium

from pycoin import ecdsa

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

    def test_standard_signature(self):
        # borrowed from pycoin tests in large part
        def do_test(secret_exponent, val_list):
            signature = Signature.make(r=0, s=0, pubkey_x=0, pubkey_y=0)
            for v in val_list:
                signature.sign(secret_exponent, v)
                signature.assert_valid_signature(v)
                signature.s = signature.s+1
                self.assertRaises(encodium.ValidationError, signature.assert_valid_signature, message=v)

        val_list = [100,20000,30000000,4000000000,500000000000,60000000000000]

        do_test(0x1111111111111111111111111111111111111111111111111111111111111111, val_list)
        do_test(0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd, val_list)
        do_test(0x47f7616ea6f9b923076625b4488115de1ef1187f760e65f89eb6f4f7ff04b012, val_list)

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
            tx = Tx.make(dapp=b'',value=5,fee=0,data=[b'ANDY'])
            tx.sender = int.from_bytes(b'MAX', 'big')
            self.state_maker._process_tx(tx)
            end_state = {
                int.from_bytes(b'MAX', 'big'): 10,
                int.from_bytes(b'ANDY', 'big'): 5
            }
            self.assertEqual(end_state, self.state_maker.super_state[b''].complete_kvs())

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
            self.assertEqual(mid_state, self.state_maker.super_state[b''].complete_kvs())

            tx = Tx.make(dapp=b'',value=5,fee=0,data=[b'ANDY'])
            super_tx = SuperTx.make(txs=[tx],signature=Signature.make(r=0, s=0, pubkey_x=0, pubkey_y=0))
            super_tx.sign(0x1111111111111111111111111111111111111111111111111111111111111111)
            super_tx.assert_internal_consistency()
            tx.sender = int.from_bytes(b'MAX', 'big')
            self.state_maker._add_super_txs([super_tx])
            end_state = {
                int.from_bytes(b'MAX', 'big'): 10,
                int.from_bytes(b'ANDY', 'big'): 5
            }
            self.assertEqual(end_state, self.state_maker.super_state[b''].complete_kvs())

            tx1 = Tx.make(dapp=b'', value=3, fee=0, data=[b'ANDY'])
            tx2 = Tx.make(dapp=b'', value=5, fee=0, data=[b'MAX'])
            super_tx = SuperTx.make(txs=[tx1, tx2], signature=Signature.make(r=0, s=0, pubkey_x=0, pubkey_y=0))
            super_tx.sign(0x1111111111111111111111111111111111111111111111111111111111111111)
            tx1.sender = int.from_bytes(b'MAX', 'big')
            tx2.sender = int.from_bytes(b'ANDY', 'big')
            super_tx.assert_internal_consistency()
            self.state_maker._add_super_txs([super_tx])
            real_end_state = {
                int.from_bytes(b'MAX', 'big'): 12,
                int.from_bytes(b'ANDY', 'big'): 3,
            }
            self.assertEqual(real_end_state, self.state_maker.super_state[b''].complete_kvs())


    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()