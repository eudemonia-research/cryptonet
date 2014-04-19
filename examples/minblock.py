#!/usr/bin/env python3

from encodium import *

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.datastructs import MerkleTree
from cryptonet.errors import ValidationError
from cryptonet.gpdht import Chain, ghash

chainVars = ChainVars()

chainVars.seeds = []
chainVars.genesisBinary = b'\x01\x01\x00'
chainVars.mine = True
chainVars.address = ('',0)

m = Cryptonet(chainVars)

@m.block
class MinBlock(Field):
    def init(self):
        self.parenthash = self.prevblock
        self.height = 1

    def fields():
        prevblock = Integer(length=32)
    
    def assertInternalConsistency(self):
        assert self.prevblock < 2**256
        assert self.prevblock >= 0
    
    def assertValidity(self, chain):
        self.assertInternalConsistency()
        
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
    miner = Miner(m.chain, m.seekNBuild)
    miner.mine(genB)
