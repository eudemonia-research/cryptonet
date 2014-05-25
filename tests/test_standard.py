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
        # found here: https://github.com/cryptosphere/rbnacl/commit/72fabf2f978ea03b75ee25a226e27bb731a8d566
        # lots of samples here: http://ed25519.cr.yp.to/python/sign.input
        privkey = int.from_bytes(unhexlify("b18e1d0045995ec3d010c387ccfeb984d783af8fbb0f40fa7db126d889f6dadd"), 'big')
        pubkey = int.from_bytes(unhexlify("77f48b59caeda77751ed138b0ec667ff50f8768c25d48309a8f386a2bad187fb"), 'big')
        signature = Signature.make(sig_bytes=b'', pubkey=pubkey)
        message = unhexlify("916c7d1d268fc0e77c1bef238432573c39be577bbea0998936add2b50a653171" +
                            "ce18a542b0b7f96c1691a3be6031522894a8634183eda38798a0c5d5d79fbd01" +
                            "dd04a8646d71873b77b221998a81922d8105f892316369d5224c9983372d2313" +
                            "c6b1f4556ea26ba49d46e8b561e0fc76633ac9766e68e21fba7edca93c4c7460" +
                            "376d7f3ac22ff372c18f613f2ae2e856af40")
        sig_bytes = unhexlify("6bd710a368c1249923fc7a1610747403040f0cc30815a00f9ff548a896bbda0b" +
                              "4eb2ca19ebcf917f0f34200a9edbad3901b64ab09cc5ef7b9bcc3c40c0ff7509")

        signature.sign(message, privkey)
        self.assertEqual(signature.sig_bytes, sig_bytes)

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
            tx = Tx.make(dapp=b'',value=5,fee=0,data=[b'ANDI'])
            super_tx = SuperTx.make(nonce=0,txs=[tx],signature=Signature.make(sig_bytes=b'', pubkey=0))
            tx.sender = int.from_bytes(b'MAX', 'big')
            self.state_maker._add_super_txs([super_tx])
            end_state = {
                int.from_bytes(b'MAX', 'big'): 10,
                int.from_bytes(b'ANDI', 'big'): 5
            }
            self.assertEqual(end_state, self.state_maker.super_state[b''].complete_kvs())


    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()