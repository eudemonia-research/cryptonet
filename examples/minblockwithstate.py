#!/usr/bin/env python3

import encodium

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.utilities import global_hash
from cryptonet.errors import ValidationError
from cryptonet.debug import debug

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
            old_head = chain.head
            # this is possibly the stupidest way to check validity, but must be done, I suppose
            try:
                old_head.reorganisation(self, chain)
            except ValidationError as e:
                pass
            chain.head.reorganisation(old_head, chain)
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

    def reorganisation(self, new_head, chain):
        ''' self.reorganisation() should be called on current head, where other_block is
        to become the new head of the chain.
        This should be called for _every_ block: adding to the head is just a trivial re-org.

        Steps:
        10. Find lowest common ancestor (LCA).
        20. Get prune level from the StateMaker (Will be lower or equal to the LCA in terms of depth).
        30. Prune to that point.
        40. Re-evaluate state from that point to new head.
        '''
        max_prune_height = chain.find_lca(self.get_hash(), new_head.get_hash()).height
        prune_point = self.state_maker.find_prune_point(max_prune_height)
        self.state_maker.prune_to_or_beyond(prune_point)
        chain.prune_to_height(prune_point)
        new_chain_path = chain.construct_chain_path(chain.head, new_head)
        chain.apply_chain_path(new_chain_path)
        self.state_maker.apply_chain_path(new_chain_path)

        ''' Inherit StateMaker, SuperState, etc from other_block.
        Remove other_block's access to StateMaker, etc.
        '''
        new_head.state_maker = self.state_maker
        self.state_maker = None
        new_head.super_state = self.super_state
        self.super_state = None

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
