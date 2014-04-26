#!/usr/bin/env python3

import encodium

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.utilities import global_hash
from cryptonet.errors import ValidationError
from cryptonet.debug import debug
from cryptonet.statemaker import StateMaker

chain_vars = ChainVars()

chain_vars.seeds = []
chain_vars.genesis_binary = b'\x01\x01\x00\x01\x00\x01\x00\x01\x00'
chain_vars.mine = True
chain_vars.address = ('',0)

min_net = Cryptonet(chain_vars)



@min_net.block
class MinBlockWithState(encodium.Field):
    ''' Minimum specification needed for functional Chain.
    See cryptonet.skeleton for unencumbered examples.
    '''

    def fields():
        parent_hash = encodium.Integer(length=32)
        height = encodium.Integer(length=4, default=0)
        nonce = encodium.Integer(length=1, default=0)
        state_root = encodium.Integer(length=32, default=0)

    def init(self):
        self.priority = self.height
        self.state_maker = None
        
    def __hash__(self):
        return self.get_hash()
    
    def assert_internal_consistency(self):
        self.assert_true(self.parent_hash >= 0 and self.parent_hash < 2**256, 'Parent hash in valid range')
        self.assert_true(self.nonce >= 0 and self.nonce < 256, 'Nonce within valid range')
    
    def assert_validity(self, chain):
        self.assert_internal_consistency()
        if chain.initialized:
            #debug('assert_validity: parent_hash : %064x' % self.parent_hash)
            assert chain.has_block_hash(self.parent_hash)
            assert chain.get_block(self.parent_hash).height + 1 == self.height
            # use chain head to do a non-permanent trial.
            valid = self.chain.head.state_maker.trail_chain_path_non_permanent()
        else:
            assert self.height == 0
            assert self.parent_hash == 0
        
    def to_bytes(self):
        return b''.join([
            self.parent_hash.to_bytes(32, 'big'),
            self.height.to_bytes(4, 'big'),
            self.nonce.to_bytes(1, 'big'),
        ])
        
    def get_hash(self):
        return global_hash(self.to_bytes())
        
    def get_candidate(self, chain):
        candidate = MinBlockWithState.make(parent_hash=self.get_hash(), height=self.height+1)
        return candidate
        
    def increment_nonce(self):
        self.nonce += 1
        
    def valid_proof_of_work(self):
        return True
        
    def better_than(self, other):
        return self.height > other.height

    def reorganisation(self, chain, from_block, around_block, to_block, is_test=False):
        ''' self.reorganisation() should be called on current head, where to_block is
        to become the new head of the chain.

        Steps:
        10. From around_block find the prune point
        20. Get prune level from the StateMaker (Will be lower or equal to the LCA in terms of depth).
        30. Prune to that point.
        40. Re-evaluate state from that point to new head.

        if is_test == True then no permanent changes are made.
        '''
        success = self.state_maker.reorganisation(chain, from_block, around_block, to_block, is_test)
        if success:
            ''' Inherit StateMaker, SuperState, etc from other_block.
            Remove other_block's access to StateMaker, etc.
            '''
            to_block.state_maker = self.state_maker
            self.state_maker = None
            to_block.super_state = self.super_state
            self.super_state = None
        return success

    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError('MinBlock: ValidationError: %s' % message)
        

def make_genesis():
    genesis_block = MinBlock.make(parent_hash=0,height=0)
    miner = Miner(min_net.chain, min_net.seek_n_build)
    miner.mine(genesis_block)

if __name__ == "__main__":
    #make_genesis()
    min_net.run()
