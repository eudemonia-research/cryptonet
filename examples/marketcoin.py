#!/usr/bin/env python3

from binascii import unhexlify

from cryptonet import Cryptonet
from cryptonet.dapp import Dapp
from cryptonet.utilities import global_hash, dsha256R
from cryptonet.datastructs import MerkleBranchToRoot

from encodium import *

BTC_CHAINHEADERS = b'BTC_CHAINHEADERS'
BTC_SPV = b'BTC_SPV'

#marketcoin = Cryptonet()

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
    GENESIS_BYTES = unhexlify("0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c")

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

#@marketcoin.dapp(BTC_CHAINHEADERS)
class BitcoinChainheaders(Chainheaders):
    # Starts at block 300,000
    GENESIS_HASH = 0x000000000000000082ccf8f1557c5d40b21edabb18d2d691cfbf87118bac7254
    GENESIS_BYTES = unhexlify(
        "020000007ef055e1674d2e6551dba41cd214debbee34aeb544c7ec670000000000000000d3998963f80c5bab43fe8c26228e98d030edf4dcbe48a666f5c39e2d7a885c9102c86d536c890019593a470d")

    HEADER_CLASS = BitcoinHeader

#@marketcoin.dapp(BTC_SPV)
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
        self.assert_true(tx_hash in self.super_state[BTC_CHAINHEADERS], 'tx_hash exists')

        header_bytes = self.super_state[BTC_CHAINHEADERS][tx_hash]
        header = BitcoinHeader.make_from_bytes(header_bytes)
        header.assert_internal_consistency()  # this checks we're actually dealing with a header
        self.assert_true(header.get_hash() == block_hash, 'provided hash is correct')

        def pair_up(l):
            return [(l[i], l[i+1]) for i in range(0, len(l), 2)]

        def bisect(l):
            return ([t[0] for t in l], [t[1] for t in l])

        merkle_prep = bisect(pair_up(tx.data[2:]))
        merkle_root = MerkleBranchToRoot.make(hash=block_hash, lr_branch=merkle_prep[0], hash_branch=merkle_prep[1]).get_hash()
        self.assert_true(merkle_root == header.merkle_root, 'merkle_roots must match')

        self.state[tx_hash ^ block_hash] = 1


#@marketcoin.dapp(b'BTC_MARKET')
class BitcoinMarket(Dapp):
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

    @staticmethod
    def on_block(workingState, block, chain):
        ''' Test for market execution condition and if so execute. '''
        return workingState

    @staticmethod
    def on_transaction(workingState, tx, chain):
        ''' Depending on tx either insert, cancel, fulfill, or _ specified order '''
        return workingState




