#!/usr/bin/env python3

from encodium import *

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.datastructs import MerkleTree
from cryptonet.errors import ValidationError
from cryptonet.gpdht import Chain, ghash

chain_vars = ChainVars()

chain_vars.seeds = []
chain_vars.genesisBinary = b'\x01\x01\x00'
chain_vars.mine = True
chain_vars.address = ('',0)

m = Cryptonet(chain_vars)

@m.block
class MinBlock(Field):
    def init(self):
        self.parenthash = self.prevblock
        self.height = 1

    def fields():
        prevblock = Integer(length=32)
    
    def assert_internal_consistency(self):
        assert self.prevblock < 2**256
        assert self.prevblock >= 0
    
    def assertValidity(self, chain):
        self.assert_internal_consistency()
        
    def __hash__(self):
        return self.getHash()
        
    def getHash(self):
        return ghash(b''.join([
            self.prevblock.to_bytes(32, 'big')
        ]))
        
    def getCandidate(self, chain):
        return MinBlock.make(prevblock = self.getHash(), height=self.height+1)
        
    def incrementNonce(self):
        pass
        
    def validPoW(self):
        return True
        
    def betterThan(self, other):
        return True
        
m.run()

def makeGenesis():
    genB = MinBlock.make(prevblock=0)
    miner = Miner(m.chain, m.seek_n_build)
    miner.mine(genB)
