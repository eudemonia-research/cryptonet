#!/usr/bin/env python3

import unittest
from cryptonet.datastructs import *
from cryptonet.gpdht import *
from cryptonet import rlp
#from examples.gracht import Header, Uncles

class TestGracht(unittest.TestCase):
    pass
    #def test_header(self):
        #genesisHeader = Header([BANT("0001", True), BANT("00000000", True), BANT("ffffff01", True), BANT("0100", True), BANT("0000534133e0", True), BANT("00000001", True), BANT("0000000000000000000000000000000000000000000000000000000000000000", True), BANT("0000000000000000000000000000000000000000000000000000000000000000", True)], Uncles([]))
        #self.assertTrue(genesisHeader.getHash() == BANT("5428e1798a6e841a9cd81a30ec8e8e68a579fa7e5f4b81152b957052d73ddd98", True))
        
    
class TestCryptonet(unittest.TestCase):
    
    def test_MerkleTree(self):
        msg1 = int.from_bytes(b'M\x9b\x99g=\xaao\xbb\xa1a\xa8\xef2\xcb\x0e\xcd\xf9]\x8d\xc9L1\xbd\x0cU\x85\xa1Wj\xedpS', 'big')
        msg2 = int.from_bytes(b'\xf6Y\x92\xe8\x9d\xce\xbb\xf8\x93\xbb\xd8z\xd9\x9d\xf9\xb7\x02\xa5l\xbccu\xebX\x9c\xf9mf\x12\x8e\x86\xcb', 'big')
        mt = MerkleLeavesToRoot.make(leaves=[msg1, msg2])
        self.assertEqual(mt.root, int.from_bytes(b"\x07B\x91\xaf\x1d\xe9\xd6\x8a'\x15G3\x85\x95\x9a\x83\xd6.9\x9e\x90\xfag/\x90\x04\xfe\xe0\xc9\xe8\x81\xcf", 'big'))
        
        mt = MerkleLeavesToRoot.make(leaves=[msg1, msg2, msg1, msg2])
        self.assertEqual(mt.root, 89752586187535061124859689857005670910448617032952735280732624523812978565650)


# Borrowed from Spore
class TestRLP(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_encode(self):
        encoded = rlp.serialize([ [], [[]], [ [], [[]] ] ])
        self.assertEqual(encoded, bytes([ 0xc7, 0xc0, 0xc1, 0xc0, 0xc3, 0xc0, 0xc1, 0xc0 ]))

        encoded = rlp.serialize(ALL_BANT([b'cat',b'dog']))
        self.assertEqual(encoded, bytes([ 0xc8, 0x83 ]) + b'cat' + bytes([0x83]) + b'dog')

        # Empty string.
        self.assertEqual(rlp.serialize(ALL_BANT(b'')), bytes([ 0x80 ]))

        # Empty list.
        self.assertEqual(rlp.serialize([]), bytes([ 0xc0 ]))

        # b'\x0f'
        self.assertEqual(rlp.serialize(ALL_BANT(b'\x0f')), bytes([0x0f]))
        
        #slow
        #big_list = [ [ BANT(b'', padTo=1024) ] * 1024 ]
        #self.assertEqual(rlp.deserialize(rlp.serialize(big_list)), big_list)

        data = BANT(b'Lorem ipsum dolor sit amet, consectetur adipisicing elit')
        encoded = rlp.serialize(data)
        decoded = rlp.deserialize(encoded)
        self.assertEqual(data, decoded)


if __name__ == '__main__':
    unittest.main()
