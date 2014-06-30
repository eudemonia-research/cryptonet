#!/usr/bin/env python3

import unittest

from cryptonet.datastructs import *


class TestStructs(unittest.TestCase):
    
    def test_IntList(self):
        cases = [
            [0,1,2,3,4,5,6,7,8,9],
        ]
        
        for case in cases:
            caseField = IntList(contents=case)
            self.assertEqual(len(caseField), len(case))
            for i in range(len(case)):
                self.assertEqual(caseField[i], case[i])
            for c in (case, caseField):
                c.append(23)
            self.assertEqual(caseField, case)


class TestCryptonet(unittest.TestCase):
    
    def test_MerkleTree(self):
        msg1 = int.from_bytes(b'M\x9b\x99g=\xaao\xbb\xa1a\xa8\xef2\xcb\x0e\xcd\xf9]\x8d\xc9L1\xbd\x0cU\x85\xa1Wj\xedpS', 'big')
        msg2 = int.from_bytes(b'\xf6Y\x92\xe8\x9d\xce\xbb\xf8\x93\xbb\xd8z\xd9\x9d\xf9\xb7\x02\xa5l\xbccu\xebX\x9c\xf9mf\x12\x8e\x86\xcb', 'big')
        mt = MerkleLeavesToRoot(leaves=[msg1, msg2])
        self.assertEqual(mt.root, int.from_bytes(b"\x07B\x91\xaf\x1d\xe9\xd6\x8a'\x15G3\x85\x95\x9a\x83\xd6.9\x9e\x90\xfag/\x90\x04\xfe\xe0\xc9\xe8\x81\xcf", 'big'))
        
        mt = MerkleLeavesToRoot(leaves=[msg1, msg2, msg1, msg2])
        self.assertEqual(mt.root, 89752586187535061124859689857005670910448617032952735280732624523812978565650)




if __name__ == '__main__':
    unittest.main()
