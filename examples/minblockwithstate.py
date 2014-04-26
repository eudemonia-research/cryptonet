#!/usr/bin/env python3

import encodium

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.utilities import global_hash
from cryptonet.errors import ValidationError
from cryptonet.debug import debug
from cryptonet.statemaker import StateMaker
from cryptonet.dapp import Dapp

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
        self.super_state = None
        self.super_txs = []
        
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
            # TODO : should we test a re-org?
            # Since reorganising will mark blocks invalid if something breaks, we don't need to waste the work
            # checking full validity.
        else:
            assert self.height == 0
            assert self.parent_hash == 0
        cur = self.state_maker.super_state[b'']
        while cur.height > 0:
            debug('Block.assert_validity: all states', cur.key_value_store)
            print(cur, cur.height)
            cur = cur.parent
        debug('Block.assert_validity: state: %s' % self.state_maker.super_state[b''].key_value_store, self.height)
        self.assert_true(self.state_maker.super_state[b''][0] == self.height, 'State records height')
        
    def to_bytes(self):
        return b''.join([
            self.parent_hash.to_bytes(32, 'big'),
            self.height.to_bytes(4, 'big'),
            self.nonce.to_bytes(1, 'big'),
            self.state_root.to_bytes(32, 'big')
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

    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError('MinBlock: ValidationError: %s' % message)

    def on_genesis(self, chain):
        assert not chain.initialized
        self.state_maker = StateMaker(chain)
        self.super_state = self.state_maker.super_state

        class Counter(Dapp):

            def on_block(self, block, chain):
                if block.height > 0:
                    debug('Counter: on_block, parent state:', self.state.parent.key_value_store)
                    debug('Counter: on_block called.', self.state.key_value_store)
                    self.state[0] = self.state[0] + 1
                    debug('Counter: on_block called.', self.state.key_value_store)

            def on_transaction(self, subtx, block, chain):
                pass

        self.state_maker.register_dapp(Counter(b'', self.state_maker))

    def set_state_maker(self, state_maker):
        self.state_maker = state_maker
        self.super_state = state_maker.super_state


def make_genesis():
    genesis_block = MinBlock.make(parent_hash=0,height=0)
    miner = Miner(min_net.chain, min_net.seek_n_build)
    miner.mine(genesis_block)

if __name__ == "__main__":
    #make_genesis()
    min_net.run()
