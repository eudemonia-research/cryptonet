from encodium import *
#import nacl.signing

import cryptonet
import cryptonet.chain
from cryptonet.utilities import global_hash
from cryptonet.statemaker import StateMaker
from cryptonet.rpcserver import RPCServer
from cryptonet.datastructs import MerkleLeavesToRoot
from cryptonet.dapp import Dapp
from cryptonet.debug import debug

class Signature(Field):

    def fields():
        v = Integer(length=1)
        r = Integer(length=32)
        s = Integer(length=32)

    def to_bytes(self):
        return b''.join([
            self.v.to_bytes(1, 'big'),
            self.r.to_bytes(32, 'big'),
            self.s.to_bytes(32, 'big'),
        ])

    def check_valid_signature(self):
        pass

    def get_hash(self):
        return global_hash(self.to_bytes())

class Tx(Field):
    
    def fields():
        dapp = Bytes()
        value = Integer(length=8)
        fee = Integer(length=4)
        data = List(Bytes(), default=[])
    
    def to_bytes(self):
        return b''.join([
            self.dapp,
            self.value.to_bytes(8, 'big'),
            self.fee.to_bytes(4, 'big'),
            b''.join(self.data)
        ])
    
    def get_hash(self):
        return global_hash(self.to_bytes())
        
        
class SuperTx(Field):
    
    def fields():
        nonce = Integer(length=4)
        txs = List(Tx())
        signature = Signature()
        
    def to_bytes(self):
        return b''.join([
            self.nonce.to_bytes(4, 'big'),
            b''.join([x.to_bytes for x in self.txs]),
            self.signature.to_bytes()
        ])
        
    def get_hash(self):
        return global_hash(self.to_bytes())

        
class Header(Field):
    
    def fields():
        version = Integer(length=2)
        nonce = Integer(length=8) # nonce second to increase work needed for PoW
        timestamp = Integer(length=5)
        target = Integer(length=32)
        sigma_diff = Integer(length=32)
        state_mr = Integer(length=32)
        transaction_mr = Integer(length=32)
        uncles_mr = Integer(length=32, default=0)
        previous_blocks = List(Integer(length=32))
        
    def to_bytes(self):
        return b''.join([
            self.version.to_bytes(2,'big'),
            self.nonce.to_bytes(8, 'big'),
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
        ''' self.assert_internal_consistency should validate the following:
        * version as expected
        * nonce not silly
        * timestamp not silly
        * target not silly
        * whatever_mr not silly
        * previous_blocks not silly
        
        'not silly' means the data 'looks' right (length, etc) but the information
        is not validated.
        '''
        pass
        
    def assert_validity(self, chain):
        ''' self.assert_validity does not validate merkle roots.
        Since the thing generating the merkle roots is stored in the block, a
        block is invlalid if its list of whatever does not produce the correct
        whatever_mr. The header is not invalid, however.
        
        self.assert_validity should validate the following:
        * self.timestamp no more than 15 minutes in the future and >= median of 
            last 100 blocks.
        * self.target is as expected based on past blocks
        * self.previous_blocks exist and are correct
        '''
        pass

    def increment_nonce(self):
        self.nonce += 1


class Block(Field):
    
    def fields():
        header = Header()
        uncles = List(Header())
        super_txs = List(SuperTx(), default=[])
        
    def init(self):
        self.parent_hash = self.header.previous_blocks[0]
        self.state_maker = None
        self.super_state = None

    def __eq__(self, other):
        if isinstance(other, Block) and other.get_hash() == self.get_hash():
            return True
        return False

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
            to_block.set_state_maker(self.state_maker)
        return success
        
    def get_hash(self):
        return self.header.get_hash()

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
        pass
        
    def assert_validity(self, chain):
        ''' self.assert_validity should validate the following:
        * self.header.state_mr equals root of self.super_state
        '''
        pass

    def better_than(self, other):
        if other == None:
            return True
        return self.header.sigma_diff > other.header.sigma_diff

    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError('Block Failed Validation: %s' % message)

    def get_candidate(self, chain):
        # todo : fix so state_root matches expected
        return self.state_maker.future_block

    def get_pre_candidate(self, chain):
        # fill in basic info here, state_root and tx_root will come later
        # todo : probably shouldn't reference _Block from chain and just use local object
        return chain._Block.make(parent_hash=self.get_hash(), height=self.height+1)

    def increment_nonce(self):
        self.header.increment_nonce()

    def valid_proof(self):
        return True

    def on_genesis(self, chain):
        assert not chain.initialized
        self.set_state_maker(StateMaker(chain))
        debug('Block.on_genesis called')

        self.setup_rpc()

    def set_state_maker(self, state_maker):
        self.state_maker = state_maker
        self.super_state = state_maker.super_state

    def update_roots(self):
        self.state_root = self.state_maker.super_state.get_hash()
        self.tx_root = MerkleLeavesToRoot.make(leaves=self.super_txs).get_hash()

    def setup_rpc(self):
        self.rpc = RPCServer(port=32550)

        @self.rpc.add_method
        def getinfo(*args):
            state = self.state_maker.super_state[b'']
            keys = state.all_keys()
            return {
                "balance": max(keys),
                "height": max(keys),
            }

        self.rpc.run()


    
        
    
