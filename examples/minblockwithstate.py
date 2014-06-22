#!/usr/bin/env python3

import encodium

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.utilities import global_hash
from cryptonet.errors import ValidationError
from cryptonet.debug import debug, print_traceback
from cryptonet.statemaker import StateMaker
from cryptonet.dapp import Dapp
from cryptonet.datastructs import MerkleLeavesToRoot
from cryptonet.rpcserver import RPCServer

chain_vars = ChainVars()

chain_vars.seeds = []
chain_vars.genesis_binary = b'\x01\x01\x00\x01\x00\x01\x01 h\x17\x0b\xf1\xa6$p\xde\xfen\x81\x8d\xablbf\x93\xc0\x96\xd2Qy\x02\x00\x19\xd7\xa7\xb2\x01\x14\xd23\x01\x00'
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
        tx_root = encodium.Integer(length=32, default=0)

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
            self.assert_true(chain.has_block_hash(self.parent_hash), 'Parent unknown')
            self.assert_true(chain.get_block(self.parent_hash).height + 1 == self.height, 'Height requirement')
            self.assert_true(self.super_state.get_hash() == self.state_root, 'State root must match expected')
        else:
            self.assert_true(self.height == 0, 'Genesis req.: height must be 0')
            self.assert_true(self.parent_hash == 0, 'Genesis req.: parent_hash must be zeroed')
        
    def to_bytes(self):
        return b''.join([
            self.parent_hash.to_bytes(32, 'big'),
            self.height.to_bytes(4, 'big'),
            self.nonce.to_bytes(1, 'big'),
            self.state_root.to_bytes(32, 'big'),
            self.tx_root.to_bytes(32, 'big')
        ])
        
    def get_hash(self):
        return global_hash(self.to_bytes())
        
    def get_candidate(self, chain):
        # todo : fix so state_root matches expected
        return self.state_maker.future_block

    def get_pre_candidate(self, chain):
        # fill in basic info here, state_root and tx_root will come later
        candidate = chain._Block.make(parent_hash=self.get_hash(), height=self.height+1)
        return candidate

    def increment_nonce(self):
        self.nonce += 1

    def valid_proof(self):
        return True
        
    def better_than(self, other):
        if other == None:
            return True
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
            to_block._set_state_maker(self.state_maker)
        return success

    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError('Block Failed Validation: %s' % message)

    def on_genesis(self, chain):
        assert not chain.initialized
        self.state_maker = StateMaker(chain)
        self.super_state = self.state_maker.super_state
        debug('Block.on_genesis called')

        class Counter(Dapp):

            def on_block(self, block, chain):
                if block.height > 0:
                    last_value = self.state[block.height - 1]
                    if last_value > 1:
                        if last_value % 2 == 0:
                            self.state[block.height] = last_value // 2
                        else:
                            self.state[block.height] = 3 * last_value + 1
                    else:
                        self.state[block.height] = block.height
                    debug('Counter: on_block called.', self.state.key_value_store)
                    self.state.recursively_print_state()

            def on_transaction(self, subtx, block, chain):
                pass

        self.state_maker.register_dapp(Counter(b'', self.state_maker))

        self.setup_rpc()

    def _set_state_maker(self, state_maker):
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

def make_genesis():
    genesis_block = MinBlockWithState.make(parent_hash=0,height=0)
    genesis_block._set_state_maker(StateMaker(min_net.chain, MinBlockWithState))
    genesis_block.update_state_root()
    miner = Miner(min_net.chain, min_net.seek_n_build)
    miner.mine(genesis_block)
    debug('Genesis Block: ', genesis_block.serialize())

if __name__ == "__main__":
    #make_genesis()
    min_net.run()
