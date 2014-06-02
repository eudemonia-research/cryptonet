import unittest

from binascii import unhexlify, hexlify

from cryptonet.utilities import sha256, dsha256, dsha256R, global_hash

class TestTransactions(unittest.TestCase):

    def setUp(self):
        pass

    def test_hashes(self):
        self.assertTrue(sha256(b'test') == unhexlify("9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"))
        self.assertTrue(dsha256(b'test') == unhexlify("954d5a49fd70d9b8bcdb35d252267829957f7ef7fa6c74f88419bdc5e82209f4"))
        self.assertTrue(dsha256R(b'test') == unhexlify("f40922e8c5bd1984f8746cfaf77e7f9529782652d235dbbcb8d970fd495a4d95"))
        self.assertTrue(global_hash(b'test') == 70622639689279718371527342103894932928233838121221666359043189029713682937432)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()