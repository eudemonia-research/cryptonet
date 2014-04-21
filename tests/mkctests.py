#!/usr/bin/env python3

import unittest
import marketcoin.bitcoin import ChainHeaders, Block as BitcoinBlock
import marketcoin import Transaction
from hashlib import sha256 as shitty_sha256
import binascii

def sha256(data):
    a = shitty_sha256()
    a.update(data)
    return a.digest()

class TestMarketcoin(unittest.TestCase):

    def test_bitcoin_chainheaders(self):

        GENESIS_BLOCK = BitcoinBlock(version=1,
                                     prevblock=0,
                                     merkleroot=0x4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b,
                                     timestamp=1231006505,
                                     bits=0x1d00ffff,
                                     nonce=2083236893)

        state = { GENESIS_BLOCK.get_hash(): GENESIS_BLOCK.as_shitty_bytes() }

        next_block_shitty_bytes = binascii.unhexlify('010000006fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000982051fd1e4ba744bbbe680e1fee14677ba1a3c3540bf7b1cdb606e857233e0e61bc6649ffff001d01e36299')

        tx = Transaction(sender=None, fee=None, amount=None, data=[next_block_shitty_bytes])

        state2 = ChainHeaders.on_transaction(state.copy(), tx, None)

        next_block_shitty_hash = sha256(sha256(next_block_shitty_bytes))

        expected_state2 = state.copy()
        expected_state2[next_block_shitty_hash] = next_block_shitty_bytes

        self.assertEqual(expected_state2, state2)

if __name__ == '__main__':
    unittest.main()
