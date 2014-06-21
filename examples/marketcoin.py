# !/usr/bin/env python3

from binascii import unhexlify
import statistics

from pycoin.tx import Tx as PycoinTx

from cryptonet import Cryptonet
from cryptonet.dapp import Dapp
from cryptonet.utilities import global_hash, dsha256R, get_varint_and_remainder, create_index, pretty_string
from cryptonet.datastructs import MerkleBranchToRoot

from encodium import *

BTC_CHAINHEADERS = b'BTC_CHAINHEADERS'
BTC_SPV = b'BTC_SPV'

# marketcoin = Cryptonet()

class BitcoinHeader(Field):
    DIFF_ONE_TARGET = 0x00000000ffff0000000000000000000000000000000000000000000000000000

    def fields():
        version = Integer(length=4)
        parent_hash = Integer(length=32)
        merkle_root = Integer(length=32)
        timestamp = Integer(length=4)
        bits = Integer(length=4)
        nonce = Integer(length=4)

    def init(self):
        self.target = BitcoinHeader.bits_to_target(self.bits)

    def to_bytes(self):
        # little endian in Bitcoin
        return b''.join([
            self.version.to_bytes(4, 'little'),
            self.parent_hash.to_bytes(32, 'little'),
            self.merkle_root.to_bytes(32, 'little'),
            self.timestamp.to_bytes(4, 'little'),
            self.bits.to_bytes(4, 'little'),
            self.nonce.to_bytes(4, 'little'),
        ])

    def get_hash(self):
        return int.from_bytes(dsha256R(self.to_bytes()), 'big')

    def valid_proof_of_work(self):
        return self.get_hash() < self.target

    def assert_internal_consistency(self):
        self.assert_true(self.valid_proof_of_work(), 'PoW must validation against target')

    def assert_valid(self, dapp):
        self.assert_internal_consistency()
        self.assert_true(dapp.state[self.parent_hash] != 0, 'Parent header must exist')

    @staticmethod
    def assert_true(condition, message):
        if not condition:
            raise ValidationError(message)

    @staticmethod
    def make_from_bytes(header_bytes):
        return BitcoinHeader.make(
            version=int.from_bytes(header_bytes[:4], 'little'),
            parent_hash=int.from_bytes(header_bytes[4:4 + 32], 'little'),
            merkle_root=int.from_bytes(header_bytes[4 + 32:4 + 32 + 32], 'little'),
            timestamp=int.from_bytes(header_bytes[4 + 32 + 32:4 + 32 + 32 + 4], 'little'),
            bits=int.from_bytes(header_bytes[4 + 32 + 32 + 4:4 + 32 + 32 + 4 + 4], 'little'),
            nonce=int.from_bytes(header_bytes[4 + 32 + 32 + 4 + 4:4 + 32 + 32 + 4 + 4 + 4], 'little'),
        )

    @staticmethod
    def bits_to_target(bits):
        # todo: does this work with signed values? See the bitcoin wiki
        bits_as_bytes = bits.to_bytes(4, 'big')
        return int.from_bytes(bits_as_bytes[1:4], 'big') * (2 ** (8 * int(bits_as_bytes[0] - 3)))

    @staticmethod
    def target_to_diff(target):
        return BitcoinHeader.DIFF_ONE_TARGET // target

    @staticmethod
    def bits_to_diff(bits):
        return BitcoinHeader.target_to_diff(BitcoinHeader.bits_to_diff(bits))


class Chainheaders(Dapp):
    ''' Chainheaders will track all provided chain headers and keep track of the longest chain.
    Initial state should have ~genesis block hash~ some recent checkpoint for Bitcoin network.

    Designed for Bitcoin-like chains

    Requirements:
    To satisfy SPV requirements we need to track a number of properties not stored in the header itself.

    * Must know top block
    * Must track ancestors incrementally - using incremental merkle tree
    * Must track height
    '''

    # These are the first blocks according to Chainheaders - can be located anywhere, doesn't need to be the actual
    # genesis blocks for the foreign chain
    GENESIS_HASH = 0
    GENESIS_BYTES = unhexlify(
        "0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c")

    HEADER_CLASS = None

    # _CHAIN offset: 0
    _CHAIN_INITIALISED = 0
    _CHAIN_GENESIS = 1
    _CHAIN_TOP_BLOCK = 2
    _CHAIN_TOP_SIGMA_DIFF = 3

    # _BLOCK offset: the block hash
    _BLOCK_HEADER_BYTES = 0
    _BLOCK_HEIGHT = 1
    _BLOCK_SIGMA_DIFF = 2
    _BLOCK_TARGET = 3
    _BLOCK_ANCESTORS_N = 10
    _BLOCK_ANCESTORS = 11

    def on_block(self, block, chain):
        if self.state[self._CHAIN_INITIALISED] == 0:  # init
            self.state[self._CHAIN_INITIALISED] = 1
            self.state[self._CHAIN_GENESIS] = self.GENESIS_HASH
            self.state[self._CHAIN_TOP_BLOCK] = self.GENESIS_HASH
            self.state[self._CHAIN_TOP_SIGMA_DIFF] = 0

            self.state[self.GENESIS_HASH + self._BLOCK_HEADER_BYTES] = self.GENESIS_BYTES
            self.state[self.GENESIS_HASH + self._BLOCK_HEIGHT] = 0
            self.state[self.GENESIS_HASH + self._BLOCK_SIGMA_DIFF] = 1
            self.state[self.GENESIS_HASH + self._BLOCK_ANCESTORS_N] = 1
            self.state[self.GENESIS_HASH + self._BLOCK_ANCESTORS + 0] = self.GENESIS_HASH

    def on_transaction(self, tx, block, chain):
        # should accept a list of block headers and validate to store the longest chain
        assert len(tx.data) > 0
        for raw_header in tx.data:
            header = self.HEADER_CLASS.make_from_bytes(raw_header)
            header.assert_valid(self)
            self.add_header_to_state(header)

    def add_header_to_state(self, header):
        block_hash = header.get_hash()
        if self.state[block_hash] != 0:
            raise ValidationError('Chainheaders: block header already added')
        self.state[block_hash + self._BLOCK_HEADER_BYTES] = header.to_bytes()
        header_height = self.state[header.parent_hash + self._BLOCK_HEIGHT] + 1
        self.state[block_hash + self._BLOCK_HEIGHT] = header_height
        sigma_diff = self.state[header.parent_hash + self._BLOCK_SIGMA_DIFF] + BitcoinHeader.bits_to_diff(header.bits)
        self.state[block_hash + self._BLOCK_SIGMA_DIFF] = sigma_diff

        # This section rolls up an incremental merkle tree
        previous_ancestors_n = self.state[header.parent_hash + self._BLOCK_ANCESTORS_N]
        previous_ancestors = []
        previous_ancestors_start_index = header.parent_hash + self._BLOCK_ANCESTORS
        for i in range(previous_ancestors_n):
            previous_ancestors.append(self.state[previous_ancestors_start_index + i])
        ancestors = previous_ancestors[:]
        j = 2
        while header_height % j == 0:
            ancestors = ancestors[:-2] + [
                global_hash(ancestors[-2].to_bytes(32, 'big') + ancestors[-1].to_bytes(32, 'big'))]
            j *= 2
        for i in range(len(ancestors)):
            self.state[block_hash + self._BLOCK_ANCESTORS + i] = ancestors[i]

        # If new head
        if sigma_diff > self.state[self._CHAIN_TOP_SIGMA_DIFF]:
            self.state[self._CHAIN_TOP_BLOCK] = block_hash
            self.state[self._CHAIN_TOP_SIGMA_DIFF] = sigma_diff


# @marketcoin.dapp(BTC_CHAINHEADERS)
class BitcoinChainheaders(Chainheaders):
    # Starts at block 300,000
    GENESIS_HASH = 0x000000000000000082ccf8f1557c5d40b21edabb18d2d691cfbf87118bac7254
    GENESIS_BYTES = unhexlify(
        "020000007ef055e1674d2e6551dba41cd214debbee34aeb544c7ec670000000000000000d3998963f80c5bab43fe8c26228e98d030edf4dcbe48a666f5c39e2d7a885c9102c86d536c890019593a470d")

    HEADER_CLASS = BitcoinHeader


# @marketcoin.dapp(BTC_SPV)
class BitcoinSPV(Dapp):
    ''' SPV and MerkleTree verification.
    SPV takes a block hash, 2 transaction hashes, and a merkle branch.
    The merkle branch should prove those two transaction hashes were included
    in the merkle tree of the header to which the block_hash belongs. Although
    this can be done with partial branches (as in the first two hashes aren't tx
    hashes, but are half way through the merkle tree) there is little benefit.
        1. Verify merkle branch is correct. Should result in MR from block
        2. Verify MR is in header 
        3. Set txhash XOR block_hash to 1

    Designed for Bitcoin-type chains'''

    def on_block(self, block, chain):
        pass

    def on_transaction(self, tx, block, chain):
        ''' Prove some BTC transaction was in some merkle tree via tx hash.
        If tx ABCD was in block 1234 then 1234 XOR ABCD will be set to 1.

        Inputs:
        block_hash
        tx_hash
        [lr, merkle_branch]...'''

        self.assert_true(len(tx.data) >= 2, 'tx_data must carry 2 or more elements to prove a tx was in a block')
        block_hash = tx.data[0]
        tx_hash = tx.data[1]
        self.assert_true(block_hash > 100000 and tx_hash > 100000, 'block_hash & tx_hash reasonable values')
        self.assert_true(block_hash in self.super_state[BTC_CHAINHEADERS], 'block_hash exists')

        header_bytes = self.super_state[BTC_CHAINHEADERS][block_hash]
        header = BitcoinHeader.make_from_bytes(header_bytes)
        header.assert_internal_consistency()  # this checks we're actually dealing with a header
        self.assert_true(header.get_hash() == block_hash, 'provided hash is correct')

        def pair_up(l):
            return [(l[i], l[i + 1]) for i in range(0, len(l), 2)]

        def unzip(l):
            return ([t[0] for t in l], [t[1] for t in l])

        merkle_prep = unzip(pair_up(tx.data[2:]))
        merkle_root = MerkleBranchToRoot.make(hash=tx_hash, lr_branch=merkle_prep[0],
                                              hash_branch=merkle_prep[1]).get_hash()
        self.assert_true(merkle_root == header.merkle_root, 'merkle_roots must match')

        self.state[tx_hash ^ block_hash] = 1


#@marketcoin.dapp(b'BTC_MARKET')
class Market(Dapp):
    ''' Market has a few functions:
        0. execute occasionally
        1. accept bids for MKC
        2. accept asks for BTC
        3. cancel order
        4. prove order fulfilled (show BTC payment)
        5. redeem pledge (if order went unfulfilled)
    First data entry decides which to do (except execution, that's automagic).
    Inputs:
    1. min_return (in MKC), max_spend (in BTC)     # output to account that provided pledge
    2. min_return (in BTC), fulfillment_requirement (output script) # max spend is tx.value
    3. order-hash or something # tx.sender is verification of ownership
    4. ordermatch id, rawtx (from BTC network), block_hash (which includes tx)
    5. 
    '''

    class NewOrder(Field):
        ''' An order as submitted in a transaction.
        '''

        LOCAL = True
        FOREIGN = False

        def fields():
            # which currency is being used, local or foreign
            local_or_foreign = Boolean()
            # maximum spend in that currency
            max_spend = Integer(length=8)
            min_return = Integer(length=8)
            # see Order.RATE_CONSTANT for scaling
            offering_rate_scaled = Integer(length=16)
            # required output - zero length for XMK buy
            # must be an address so someone can't force to a non-standard output
            # addresses are 20 bytes
            pubkey_hash = Integer(length=20)


    class Order(Field):
        ''' An order as in the order book
        '''

        BID = True
        ASK = False
        RATE_CONSTANT = 256 ** 8

        def fields():
            bid_or_ask = Boolean()  # always bid FOR XMK (buy) or ask FOR XMK (sell)
            amount = Integer(length=8)
            rate = Integer(length=16)  # rate per 256**8 XMK? 19 orders of magnitude each way, probably enough
            # link in order book
            pay_to_pubkey_hash = Integer(length=20)
            sender = Integer(length=32)
            pledge = Integer(length=8)
            exact_value_out = Integer(length=8, default=0)
            next_worse_order = Integer(length=32)
            next_better_order = Integer(length=32)

        def to_bytes(self):
            return b''.join([
                '\x01' if self.bid_or_ask == self.BID else '\x00',
                self.amount.to_bytes(8, 'big'),
                self.rate.to_bytes(16, 'big'),
                self.pay_to_pubkey_hash.to_bytes(20, 'big'),
                self.sender.to_bytes(32, 'big'),
                self.pledge.to_bytes(8, 'big'),
                self.exavt_value_out.to_bytes(8, 'big'),
            ])

        def get_hash(self):
            return global_hash(self.to_bytes())

        @classmethod
        def from_new_order(cls, new_order):
            # todo: this whole method
            return cls.make()

        @classmethod
        def make_change(cls, source_order, amount=0, pledge=0):
            return cls.make(
                bid_or_ask=source_order.bid_or_ask, amount=amount, rate=source_order.rate,
                next_worse_order=source_order.next_worse_order, next_better_order=source_order.next_better_order,
                pay_to_pubkey_hash=source_order.pay_to_pubkey_hash, sender=source_order.sender, pledge=pledge
            )

        @staticmethod
        def create_match_and_change(bid, ask):
            # todo: figure out how to do rates - duh, just work in large numbers
            trade_rate = (bid.rate + ask.rate) // 2
            print('create_match_and_change', bid.rate, ask.rate, trade_rate, Market.Order.RATE_CONSTANT)
            bid_xmk = bid.amount * Market.Order.RATE_CONSTANT // trade_rate
            ask_xmk = ask.amount
            print('cmac, min bid, max ask: ', bid_xmk, ask_xmk)
            if ask_xmk == bid_xmk:
                trade_volume = bid_xmk
                change = None
                alt_pledge_amount = bid.pledge
            else:
                trade_volume = min(bid_xmk, ask_xmk)
                alt_pledge_amount = bid.pledge * bid_xmk // trade_volume
                if trade_volume == bid_xmk:  # IE there is alt change
                    change = Market.Order.make_change(ask, amount=ask_xmk - bid_xmk)
                elif trade_volume == ask_xmk:  # IE there is xmk change
                    alt_change_amount = Market.Order.calculate_rate(bid.rate, xmk=bid_xmk - trade_volume)
                    change = Market.Order.make_change(bid, amount=alt_change_amount,
                                                      pledge=bid.pledge - alt_pledge_amount)
                else:
                    raise ValidationError('Wtf, how\'d you get here?!')
            foreign_amount = Market.Order.calculate_rate(trade_rate, xmk=trade_volume)
            match = Market.OrderMatch(pay_to_pubkey_hash=ask.pay_to_pubkey_hash, success_output=bid.sender,
                                      fail_output=ask.sender, foreign_amount=foreign_amount, local_amount=trade_volume,
                                      pledge_amount=alt_pledge_amount, rate=trade_rate)
            return (match, change)

        @staticmethod
        def calculate_rate(rate, xmk=None, alt=None):
            assert xmk != None or alt != None
            assert xmk == None or alt == None
            if xmk == None:
                return alt * Market.Order.RATE_CONSTANT // rate
            return xmk * rate // Market.Order.RATE_CONSTANT


    class OrderMatch(Field):
        ''' An order-match as stored in the state
        '''

        def fields():
            pay_to_pubkey_hash = Integer(length=20)  # PKH of seller on ALT network
            success_output = Integer(length=32)  # local pubkey_x corresponding to buyer of XMK
            fail_output = Integer(length=32)  # local pubkey_x corresponding to seller of XMK (used if buyer reneges)
            foreign_amount = Integer(length=8)
            local_amount = Integer(length=8)
            pledge_amount = Integer(length=8)
            rate = Integer(length=16)

        def to_bytes(self):
            return b''.join([
                self.pay_to_pubkey_hash.to_bytes(20, 'big'),
                self.success_output.to_bytes(32, 'big'),
                self.fail_output.to_bytes(32, 'big'),
                self.foreign_amount.to_bytes(8, 'big'),
                self.local_amount.to_bytes(8, 'big'),
                self.pledge_amount.to_bytes(8, 'big'),
                self.rate.to_bytes(16, 'big')
            ])

        def get_hash(self):
            return global_hash(self.to_bytes())

        def __str__(self):
            return pretty_string({
                'p2phk': self.pay_to_pubkey_hash,
                'success_out': self.success_output,
                'fail_out': self.fail_output,
                'foreign_amount': self.foreign_amount,
                'local_amount': self.local_amount,
                'pledge_amount': self.pledge_amount
            })


    class ProofOfPayment(Field):
        ''' Submitted to prove payment
        '''

        def fields():
            order_match_id = Integer(length=32)
            tx_bytes = Bytes()

        def init(self):
            self.transaction = PycoinTx.parse(self.tx_bytes)

        def to_bytes(self):
            return b''.join([
                self.order_match_id.to_bytes(32, 'big'),
                self.tx_bytes
            ])

        def get_hash(self):
            return global_hash(self.to_bytes())


    class CancelOrder(Field):
        ''' Message to cancel order
        '''

        def fields():
            order_id = Integer(length=32)


    class RedeemPledge(Field):
        ''' Submitted by seller (or anyone) of XMK to redeem the pledge if buyer reneges.
        '''

        def fields():
            order_match_id = Integer(length=32)

    _ACTIONS = create_index(['new', 'cancel', 'fulfill', 'redeem'])

    # this maps market metadata, including target frequency for market execution
    _METADATA = create_index(['lowest_trade', 'highest_trade', 'best_bid', 'best_ask', 'volume',
                              'mean', 'standard_deviation', 'target_period'])

    # this is how we find our way between states; track the start of each side of the orderbook.
    _STATE_INDEX = create_index(['ob_best_bid', 'ob_best_ask'])

    def on_block(self, block, chain):
        ''' Test for market execution condition and if so execute.

        1. Cycle through market and construct order_matches.
            1. get top orders
            2. ensure sell_price <= buy_price
            3. create an order_match
            4. calculate change and set appropriate top order
            5. go to (0)
        '''

        def lookup_period_metadata(block_hash, index):
            return self.state[block_hash - index]

        # unused for the moment
        def set_period_metadata(block_hash, index, content):
            self.state[block_hash - index] = content

        highest_trade = 0
        lowest_trade = 2 ** 64 - 1
        volume = 0

        trades = []
        ordermatches = []

        this_bid_hash = self.state[Market._STATE_INDEX['ob_best_bid']]
        this_ask_hash = self.state[Market._STATE_INDEX['ob_best_ask']]
        this_bid = self.state[this_bid_hash]
        this_ask = self.state[this_ask_hash]
        best_bid = this_bid
        best_ask = this_ask

        # as long as the bids are better than the asks matching continues
        while this_bid.rate >= this_ask.rate:
            match, change = Market.Order.create_match_and_change(this_bid, this_ask)
            # update meta and ordermatches
            ordermatches.append(match)
            volume += match.local_amount
            if match.rate > highest_trade:
                highest_trade = match.rate
            elif match.rate < lowest_trade:
                lowest_trade = match.rate
            trades.append(match.rate)
            # set next orders
            if change.bid_or_ask == Market.Order.BID:
                this_bid = change
                this_ask = self.state[this_ask.next_worst_order]
            else:
                this_bid = self.state[this_bid.next_worst_order]
                this_ask = change
        self.state[Market.Order.BID] = this_bid.get_hash()
        self.state[Market.Order.ASK] = this_ask.get_hash()
        self.state[this_bid.get_hash()] = this_bid
        self.state[this_ask.get_hash()] = this_ask

        match_counter = len(ordermatches)

        # I'm going to cheat, todo: make this something less not-python-dependent
        # the * 10000 is there to keep significant figures; we need this because we're storing ints
        mean = int(statistics.mean(trades) * 10000)
        std_dev = int(statistics.stdev(trades, mean) * 10000)

        # todo : cleanup - keep state clear of clutter

        self.update_metadata(lowest_trade, highest_trade, best_bid, best_ask, volume, mean, std_dev, lookup_period_metadata(block.header.previous_blocks[1], self._METADATA['target_period']))

        # TODO: remove old orders (>24hrs old)
        # this will be done by running through the list of orders placed 24 hours ago (or x blocks, I guess)
        # maybe orders should be rejected if they're not unique over the ENTIRE life of the chain
        # the down side is we still need to keep everything in state, which sucks and takes up lots of memory.
        # After 10^6 orders we'd use 6.4*10^7 bytes; 64 mb? Bitcoin has had (generously) 35 Million txs, the same
        # volume would mean 1.8 GB which is fucking tonnes
        # todo: solve

    def update_metadata(self, lowest_trade, highest_trade, best_bid, best_ask, volume, mean, standard_deviation, target_period):
        ''' Updates metadata about the recent price to be used when calculating required pledges.
        '''
        self.state[self._METADATA['lowest_trade']] = lowest_trade
        self.state[self._METADATA['highest_trade']] = highest_trade
        self.state[self._METADATA['best_bid']] = best_bid
        self.state[self._METADATA['best_ask']] = best_ask
        self.state[self._METADATA['volume']] = volume
        self.state[self._METADATA['mean']] = mean
        self.state[self._METADATA['standard_deviation']] = standard_deviation
        self.state[self._METADATA['target_period']] = target_period

    def on_transaction(self, tx, block, chain):
        ''' Depending on tx either insert, cancel, fulfill, or _ specified order '''
        self.assert_true(len(tx.data) == 2, 'txs to market must have two bits o data in all cases, index and serialised object')
        self.assert_true(len(tx.data[0]) == 1, 'first data element must be single byte')
        action = tx.data[0][0]  # b'123'[0] is an integer
        if action == self._ACTIONS['new']:
            self.add_new_order(tx, block, chain)
        elif action == self._ACTIONS['cancel']:
            self.cancel_order(tx, block, chain)
        elif action == self._ACTIONS['fulfill']:
            self.fulfill_order_match(tx, block, chain)
        elif action == self._ACTIONS['redeem']:
            self.redeem_pledge(tx, block, chain)
        else:
            raise ValidationError('Unknown Action')

    def add_new_order(self, tx, block, chain):
        ''' Insert order into order book.
        Orderbook is doubly linked list of orders
        Find the relevant insertion place and insert into doubly linked list.
        Also add the order to the list of orders added during that block.
        '''

        def find_insert_place(oip):
            # do something with state and find place in orderbook, what does a place in the orderbook even mean?
            pass

        def insert_into_state(oip, insert_before_this_hash):
            pass

        order_in_potentia = Market.NewOrder.make(tx[1])
        oip = order_in_potentia
        # insert order; link in relevant place, if first set in state
        # can we figure out a way of caching or getting an efficient method of searching
        order = Market.Order.from_new_order(oip)
        self.assert_true(self.state[order.get_hash()] != 0, 'Already identical order in order book, rejecting')
        insert_before_this_hash = find_insert_place(oip)
        insert_into_state(oip, insert_before_this_hash)


    def cancel_order(self, tx, block, chain):
        ''' Remove order from order book.
        '''

        def remove_order(self, order_to_remove):
            pre_order = self.state[order_to_remove.next_better]
        cancellation = Market.CancelOrder.make(tx.data[1])
        self.assert_true(self.state[cancellation.order_id] != 0, 'Order must exist')
        order_to_cancel = self.state[cancellation.order_id]
        self.assert_true(order_to_cancel.sender == tx.sender, 'Must be authorised to cancel order')


    def fulfill_order_match(self, tx, block, chain):
        ''' Prove a fulfilled order_match by providing the relevant Bitcoin tx.
        Does not require authentication.
        '''
        pass

    def redeem_pledge(self, tx, block, chain):
        ''' If 1440 (or 24hrs) blocks have passed allow the pledge to be pushed to seller.
        Does not require authentication.
        '''
        pass

    def additional_state_operations(self, state_maker):
        # pass the orderbook and ordermatchbook to block, if we go that route
        self.state_maker = state_maker






