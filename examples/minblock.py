#!/usr/bin/env python3

import encodium

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.datastructs import MerkleTree
from cryptonet.errors import ValidationError
from cryptonet.utilities import global_hash
from cryptonet.chain import Chain

chain_vars = ChainVars()

chain_vars.seeds = []
chain_vars.genesis_binary = b'\x01\x01\x00\x01\x00'
chain_vars.mine = True
chain_vars.address = ('',0)

min_net = Cryptonet(chain_vars)

@min_net.block
class MinBlock(encodium.Field):
    
    def fields():
        parent_hash = encodium.Integer(length=32)
        height = encodium.Integer(length=4, default=0)
        
    def __hash__(self):
        return self.get_hash()
    
    def assert_internal_consistency(self):
        assert self.parent_hash < 2**256
        assert self.parent_hash >= 0
    
    def assert_validity(self, chain):
        self.assert_internal_consistency()
        if chain.initialized:
            print('assert_validity: parent_hash : %064x' % self.parent_hash)
            assert chain.has_block_hash(self.parent_hash)
            assert chain.get_block(self.parent_hash).height + 1 == self.height
        else:
            assert self.height == 0
            assert self.parent_hash == 0
        
    def to_bytes(self):
        return b''.join([
            self.parent_hash.to_bytes(32, 'big'),
            self.height.to_bytes(4, 'big'),
        ])
        
    def get_hash(self):
        return global_hash(self.to_bytes())
        
    def get_candidate(self, chain):
        return MinBlock.make(parent_hash=self.get_hash(), height=self.height+1)
        
    def increment_nonce(self):
        pass
        
    def valid_proof_of_work(self):
        return True
        
    def better_than(self, other):
        return self.height > other.height
        

def make_genesis():
    genesis_block = MinBlock.make(parent_hash=0,height=0)
    miner = Miner(min_net.chain, min_net.seek_n_build)
    miner.mine(genesis_block)

if __name__ == "__main__":
    #make_genesis()
    min_net.run()
