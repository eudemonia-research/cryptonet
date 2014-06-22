import time
from binascii import unhexlify

from encodium import *
import pycoin.ecdsa

from cryptonet.utilities import global_hash, time_as_int
from cryptonet.statemaker import StateMaker
from cryptonet.rpcserver import RPCServer
from cryptonet.datastructs import MerkleLeavesToRoot
from cryptonet.dapp import TxPrism, TxTracker
from cryptonet.debug import debug
from cryptonet.constants import TX_TRACKER, ROOT_DAPP
import cryptonet

'''
Hierarchy:
BLOCK [
    HEADER
    UNCLES [
        HEADERS...
    ]
    SUPER_TXS [
        TXS...
        SIG
    ]
]

'''


class Signature(Field):
    def fields():
        r = Integer(length=32)
        s = Integer(length=32)
        pubkey_x = Integer(length=32)
        pubkey_y = Integer(length=32)

    def init(self):
        self.sender = self.pubkey_x

    def to_bytes(self):
        # TODO unsure if this will serialise (r,s) and (r,-s) the same, and (x,y) and (x,-y)
        # TODO If so this needs to change before mainnet time
        return self.r.to_bytes(32, 'big') + self.s.to_bytes(32, 'big') + \
               self.pubkey_x.to_bytes(32, 'big') + self.pubkey_y.to_bytes(32, 'big')

    def assert_valid_signature(self, message):
        '''
        '''
        # TODO assert pubkey is valid for curve
        if not pycoin.ecdsa.verify(pycoin.ecdsa.generator_secp256k1,
                                   (self.pubkey_x, self.pubkey_y),
                                   global_hash(message),
                                   (self.r, self.s)):
            raise ValidationError('Signature failed to verify')
        print('Signature.assert_valid_signature', message)

    def pubkey(self):
        return (self.pubkey_x, self.pubkey_y)

    def signature(self):
        return (self.r, self.s)

    def get_hash(self):
        return global_hash(self.to_bytes())

    def sign(self, secret_exponent, message):
        ''' Set r,s according to
        '''
        assert isinstance(message, int)
        # TODO check that we're doing this right.
        self.r, self.s = pycoin.ecdsa.sign(pycoin.ecdsa.generator_secp256k1,
                                           secret_exponent,
                                           global_hash(message))
        self.pubkey_x, self.pubkey_y = pycoin.ecdsa.public_pair_for_secret_exponent(pycoin.ecdsa.generator_secp256k1,
                                                                                    secret_exponent)
        self.sender = self.pubkey_x
        self.assert_valid_signature(message)
        print('Signature.sign', message)


class Tx(Field):
    def fields():
        dapp = Bytes()
        value = Integer(length=8)
        fee = Integer(length=4, default=0)
        donation = Integer(length=4, default=0)
        data = List(Bytes(), default=[])

    def init(self):
        #self.sender = self.recover_pubkey()
        pass

    def to_bytes(self):
        return b''.join([
            self.dapp,
            self.value.to_bytes(8, 'big'),
            self.fee.to_bytes(4, 'big'),
            self.donation.to_bytes(4, 'big'),
            b''.join(self.data)  # TODO unsafe; ['ab','cd'] and ['a','bcd'] are the same when put through this
        ])

    def get_hash(self):
        return global_hash(self.to_bytes())

    def assert_internal_consistency(self):
        pass  # if we've got this far the tx should be well formed


class SuperTx(Field):
    def fields():
        txs = List(Tx())
        signature = Signature()

    def init(self):
        self._gen_txs_bytes()
        self._set_tx_sender()

    def _gen_txs_bytes(self):
        self.txs_bytes = b''.join([tx.to_bytes() for tx in self.txs])

    def _set_tx_sender(self):
        for tx in self.txs:
            tx.sender = self.signature.pubkey_x

    def to_bytes(self):
        return b''.join([
            self.txs_bytes,
            self.signature.to_bytes(),
        ])

    def get_hash(self):
        return global_hash(self.to_bytes())

    def sign(self, secret_exponent):
        # shouldn't need to self._gen_txs_bytes() here
        self.signature.sign(secret_exponent, int.from_bytes(self.txs_bytes, 'big'))
        self._set_tx_sender()

    def assert_internal_consistency(self):
        '''Should ensure signature is valid, nonce is valid, and each tx is valid
        '''
        for tx in self.txs:
            tx.assert_internal_consistency()
        self.signature.assert_valid_signature(int.from_bytes(self.txs_bytes, 'big'))
        old_txs_bytes = self.txs_bytes
        self._gen_txs_bytes()
        assert old_txs_bytes == self.txs_bytes


class Header(Field):
    DEFAULT_TARGET = 2 ** 248
    _TARGET1 = 2 ** 256  # changed to exactly 2^256 as this is the only number with probability==1 that a hash will be
                         # strictly less than the target. Additionally, it's a bit neater on the difficulty calc side.
    RETARGET_PERIOD = 16  # Measured in blocks
    BLOCKS_PER_DAY = 1440

    def fields():
        version = Integer(length=2, default=1)
        nonce = Integer(length=8, default=0)  # nonce second to increase work needed for PoW
        height = Integer(length=4, default=0)
        timestamp = Integer(length=5, default=int(time.time()))
        target = Integer(length=32, default=Header.DEFAULT_TARGET)
        sigma_diff = Integer(length=32, default=Header.target_to_diff(Header.DEFAULT_TARGET))
        state_mr = Integer(length=32, default=0)
        transaction_mr = Integer(length=32, default=0)
        uncles_mr = Integer(length=32, default=0)
        previous_blocks = List(Integer(length=32), default=[0])

    def init(self):
        self.parent_hash = self.previous_blocks[0]

    def to_bytes(self):
        return b''.join([
            self.version.to_bytes(2, 'big'),
            self.nonce.to_bytes(8, 'big'),
            self.height.to_bytes(4, 'big'),
            self.timestamp.to_bytes(5, 'big'),
            self.target.to_bytes(32, 'big'),
            self.sigma_diff.to_bytes(32, 'big'),
            self.state_mr.to_bytes(32, 'big'),
            self.transaction_mr.to_bytes(32, 'big'),
            self.uncles_mr.to_bytes(32, 'big'),
            b''.join([i.to_bytes(32, 'big') for i in self.previous_blocks]),
        ])

    def get_hash(self):
        return global_hash(self.to_bytes())

    def assert_internal_consistency(self):
        # todo: finish
        ''' self.assert_internal_consistency should validate the following:
        * version as expected
        * timestamp not silly
        * previous_blocks not silly
        * PoW valid
        
        'not silly' means the data 'looks' right (length, etc) but the information
        is not validated.
        '''
        self.assert_true(self.version == 1, 'version at 1')
        self.assert_true(self.timestamp <= int(time.time()) + 60 * 15, 'timestamp too far in future')
        self.assert_true(self.valid_proof(), 'valid PoW required')
        self.assert_true(len(self.previous_blocks) < 30, 'reasonable number of prev_blocks')

    def assert_validity(self, chain):
        ''' self.assert_validity does not validate merkle roots.
        Since the thing generating the merkle roots is stored in the block, a
        block is invalid if its list of whatever does not produce the correct
        whatever_mr. The header is not invalid, however.

        self.assert_validity should validate the following:
        * self.timestamp is >= something
        * self.target is as expected based on past blocks
        * self.previous_blocks exist and are correct
        '''
        # todo: finish
        # todo: timestamp validation

        if chain.initialized:
            for block_hash in self.previous_blocks:
                self.assert_true(chain.has_block_hash(block_hash), 'previous_blocks required to be known')
                self.assert_true(chain.db.get_ancestors(self.parent_hash) == self.previous_blocks,
                                 'previous blocks must match expected')
            self.assert_true(chain.get_block(self.parent_hash).height + 1 == self.height, 'Height requirement')
        else:
            self.assert_true(self.height == 0, 'Genesis req.: height must be 0')
            self.assert_true(self.previous_blocks == [0], 'Genesis req.: Previous blocks must be zeroed')
            self.assert_true(self.uncles_mr == 0, 'Genesis req.: uncle_mr must be zeroed')
        self.assert_true(self.calc_expected_target(chain, chain.get_block(self.parent_hash)) == self.target,
                         'target must be as expected')
        self.assert_true(self.calc_sigma_diff(self, chain) == self.sigma_diff, 'sigma_diff must be as expected')

    def valid_proof(self):
        return self.get_hash() < self.target

    def increment_nonce(self):
        self.nonce += 1

    # todo: test
    def get_pre_candidate(self, chain, previous_block):
        new_header = Header.make(
            version=self.version,
            nonce=0,
            height=self.height + 1,
            timestamp=time_as_int(),
            previous_blocks=chain.db.get_ancestors(previous_block.get_hash()),
        )
        new_header.target = Header.calc_expected_target(new_header, chain, previous_block)
        new_header.sigma_diff = Header.calc_sigma_diff(new_header, chain)
        return new_header

    # todo: test
    def calc_expected_target(self, chain, previous_block):
        ''' Given self, chain, and previous_block, calculate the expected target.
        Currently using same method as Bitcoin
        '''
        if self.previous_blocks[0] == 0: return Header.DEFAULT_TARGET
        if self.height % Header.RETARGET_PERIOD != 0: return previous_block.header.target

        # todo: is this only going to work for retarget periods of a power of 2?
        old_ancestor = chain.get_block(self.previous_blocks[(Header.RETARGET_PERIOD - 1).bit_length()])
        timedelta = self.timestamp - old_ancestor.header.timestamp
        expected_timedelta = 60 * 60 * 24 * Header.RETARGET_PERIOD // Header.BLOCKS_PER_DAY

        if timedelta < expected_timedelta // 4:
            timedelta = expected_timedelta // 4
        elif timedelta > expected_timedelta * 4:
            timedelta = expected_timedelta * 4

        new_target = previous_block.header.target * timedelta // expected_timedelta
        debug('New Target Calculated: %064x, height: %d' % (new_target, self.height))
        return new_target

    # todo: test
    @staticmethod
    def calc_sigma_diff(header, chain):
        ''' given header, calculate the sigma_diff '''
        previous_block = chain.get_block(header.parent_hash)
        if header.previous_blocks[0] == 0:
            previous_sigma_diff = 0
        else:
            previous_sigma_diff = previous_block.header.sigma_diff
        return previous_sigma_diff + header.target_to_diff(header.target)

    @staticmethod
    def target_to_diff(target):
        return Header._TARGET1 // target

    @staticmethod
    def assert_true(condition, message):
        if not condition:
            raise ValidationError(message)


class Block(Field):
    def fields():
        header = Header()
        uncles = List(Header(), default=[])
        super_txs = List(SuperTx(), default=[])

    def init(self):
        self.parent_hash = self.header.previous_blocks[0]
        self.height = self.header.height
        self.priority = self.height
        self.state_maker = None
        self.super_state = None

    def __eq__(self, other):
        if isinstance(other, Block) and other.get_hash() == self.get_hash():
            return True
        return False

    def related_blocks(self):
        return self.header.previous_blocks

    def reorganisation(self, chain, from_block, around_block, to_block, is_test=False):
        ''' self.reorganisation() should be called only on the current head, where to_block is
        to become the new head of the chain.

                 #3--#4--
        -#1--#2<     ^-----from
                 #3a-#4a-#5a-
              ^-- around  ^---to

        If #4 is the head, and #5a arrives, all else being equal, the following will be called:
        from_block = #4
        around_block = #2
        to_block = #5a


        Steps:
        10. From around_block find the prune point
        20. Get prune level from the StateMaker (Will be lower or equal to the LCA in terms of depth).
        30. Prune to that point.
        40. Re-evaluate state from that point to new head.

        if is_test == True then no permanent changes are made.
        '''
        assert self.state_maker != None
        success = self.state_maker.reorganisation(chain, from_block, around_block, to_block, is_test)
        if success:
            to_block._set_state_maker(self.state_maker)
        return success

    def get_hash(self):
        return self.header.get_hash()

    def __hash__(self):
        return global_hash(self.serialize())

    #def add_super_txs(self, list_of_super_txs):
    #    self.state_maker.add_super_txs(list_of_super_txs)

    def assert_internal_consistency(self):
        ''' self.assert_internal_consistency should validate the following:
        * self.header internally consistent
        * self.uncles are all internally consistent
        * self.super_txs all internally consistent
        * self.header.transaction_mr equals merkle root of self.super_txs
        * self.header.uncles_mr equals merkle root of self.uncles
        '''
        self.header.assert_internal_consistency()
        for uncle in self.uncles:
            uncle.assert_internal_consistency()
        for super_tx in self.super_txs:
            super_tx.assert_internal_consistency()
        self.assert_true(self.header.transaction_mr == MerkleLeavesToRoot.make(
            leaves=[i.get_hash() for i in self.super_txs]).get_hash(), 'TxMR consistency')
        self.assert_true(
            self.header.uncles_mr == MerkleLeavesToRoot.make(leaves=[i.get_hash() for i in self.uncles]).get_hash(),
            'UnclesMR consistency')

    def assert_validity(self, chain):
        ''' self.assert_validity should validate the following:
        * self.header.state_mr equals root of self.super_state
        '''
        print(self.super_state[b''].all_keys())
        self.assert_internal_consistency()
        self.header.assert_validity(chain)
        if chain.initialized:
            self.assert_true(chain.has_block_hash(self.parent_hash), 'Parent must be known')
            self.assert_true(chain.get_block(self.parent_hash).height + 1 == self.height, 'Height requirement')
            print('#####################',self.state_maker.future_block.super_state[b''].key_value_store)
            self.assert_true(self.super_state.get_hash() == self.header.state_mr, 'State root must match expected')
        else:
            self.assert_true(self.height == 0, 'Genesis req.: height must be 0')
            self.assert_true(self.parent_hash == 0, 'Genesis req.: parent_hash must be zeroed')
            self.assert_true(self.header.state_mr == 0, 'Genesis req.: state_mr zeroed')
        # TODO The below will fail if the current block isn't at the head.
        # TODO Policy should be to only .assert_validity() on the head.

    def better_than(self, other):
        if other == None:
            return True
        return self.header.sigma_diff > other.header.sigma_diff

    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError('Block Failed Validation: %s' % message)

    @classmethod
    def get_unmined_genesis(cls):
        return Block.make(header=Header.make(), uncles=[], super_txs=[])

    def get_candidate(self, chain):
        # todo : fix so state_root matches expected - should now be fixed?
        print(self.state_maker.future_block.header.state_mr, self.super_state.get_hash())
        print(self.state_maker.future_block.super_txs)
        return self.state_maker.future_block

    def get_pre_candidate(self, chain):
        # fill in basic info here, state_root and tx_root will come later
        # todo : probably shouldn't reference _Block from chain and just use local object
        return chain._Block.make(header=self.header.get_pre_candidate(chain, self), uncles=[], super_txs=[])

    def increment_nonce(self):
        self.header.increment_nonce()

    def valid_proof(self):
        return self.header.valid_proof()

    def on_genesis(self, chain):
        debug('Block.on_genesis called')
        assert isinstance(chain, cryptonet.Chain)
        assert not chain.initialized
        self._set_state_maker(StateMaker(chain))
        # TxPrism is standard root dapp - allows for txs to be passed to contracts
        #self.state_maker.register_dapp(TxPrism(ROOT_DAPP, self.state_maker))
        #self.state_maker.register_dapp(TxTracker(TX_TRACKER, self.state_maker))

    def _set_state_maker(self, state_maker):
        assert isinstance(state_maker, StateMaker)
        self.state_maker = state_maker
        self.super_state = state_maker.super_state
        self.additional_state_operations(state_maker)

    def additional_state_operations(self, state_maker):
        assert isinstance(state_maker, StateMaker)

    def update_roots(self):
        if self.height != 0:
            debug('UPDATE_ROOTS')
            self.header.state_mr = self.state_maker.super_state.get_hash()
            self.header.transaction_mr = MerkleLeavesToRoot.make(leaves=[i.get_hash() for i in self.super_txs]).get_hash()

    def add_super_tx(self, super_tx):
        self.super_txs.append(super_tx)
        self.state_maker.ap


class RCPHandler:
    def __init__(self, cryptonet, port):
        self.cryptonet = cryptonet
        self.port = port
        self.state_maker = cryptonet.chain.head.state_maker
        self.super_state = self.state_maker.super_state
        self.setup_rpc()

    def setup_rpc(self):
        chain = self.cryptonet.chain
        p2p = self.cryptonet.p2p
        rpc = RPCServer(port=self.port)

        @rpc.add_method
        def get_info():
            return {
                "top_block hash": chain.head.get_hash(),
                "top_block_height": chain.get_height(),
                "difficulty": Header.target_to_diff(chain.head.header.target),
            }

        @rpc.add_method
        def get_balance(pubkey_x):
            assert isinstance(pubkey_x, int)
            return {
                "balance": self.super_state[b''][pubkey_x]
            }

        @rpc.add_method
        def get_ledger():
            return self.super_state[b''].complete_kvs()

        @rpc.add_method
        def push_tx(super_tx_serialised):
            print('######rpc.pushtx: stx ser\'d', super_tx_serialised)
            super_tx = SuperTx.make(unhexlify(super_tx_serialised))
            super_tx.assert_internal_consistency()
            self.state_maker.apply_super_tx_to_future(super_tx)
            chain.restart_miner()
            p2p.broadcast(b'super_tx', super_tx)
            return {"success": True, 'relayed': True}

        rpc.run()
