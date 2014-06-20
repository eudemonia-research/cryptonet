import unittest

from binascii import unhexlify

from examples.marketcoin import *


class TestTransactions(unittest.TestCase):
    def setUp(self):
        pass

    def test_bitcoin_headers(self):
        genesis_header = BitcoinHeader.make_from_bytes(unhexlify(
            "0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c"))
        genesis_header.assert_internal_consistency()

    def test_creation_match_and_change(self):
        bid_pledge = 10000
        bid = Market.Order(bid_or_ask=Market.Order.BID, amount=1000000, rate=11 * Market.Order.RATE_CONSTANT // 10,
                           next_worse_order=0, next_better_order=0, pay_to_pubkey_hash=0,
                           sender=int.from_bytes(b'MAX', 'big'), pledge=bid_pledge)
        ask = Market.Order(bid_or_ask=Market.Order.ASK, amount=1000000, rate=9 * Market.Order.RATE_CONSTANT // 10,
                           next_worse_order=0, next_better_order=0, pay_to_pubkey_hash=123456789,
                           sender=int.from_bytes(b'KIT', 'big'), pledge=0)
        match, change = Market.Order.create_match_and_change(bid, ask)
        expected_match = Market.OrderMatch(pay_to_pubkey_hash=123456789, success_output=bid.sender,
                                           fail_output=ask.sender, foreign_amount=999999, local_amount=1000000,
                                           pledge_amount=bid.pledge, rate=match.rate)
        expected_match2 = Market.OrderMatch(pay_to_pubkey_hash=123456789, success_output=bid.sender,
                                           fail_output=ask.sender, foreign_amount=999999, local_amount=1000000,
                                           pledge_amount=bid.pledge, rate=match.rate)
        expected_change = None
        print(expected_match2, expected_match)
        # todo: this fails, wtf
        self.assertEqual(expected_match2, expected_match, 'match as expected')
        self.assertEqual(match, expected_match, 'match as expected')
        self.assertTrue(expected_change == change, 'change as expected')

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()