'''gpdht.py contains functions to validate the protocol'''

import hashlib, sys
import sha3
from binascii import hexlify, unhexlify

from cryptonet.debug import *

#from utilities import *


#==============================================================================
# GENERAL CRYPTONET FUNCTIONS
#==============================================================================
    

def num2bits(n, minlen=0):
    n = int(n)
    r = []
    while n > 0:
        r.append(n%2)
        n //= 2
    pad = minlen - len(r)
    while pad > 0:
        r.append(0)
        pad -= 1
    return r[::-1]

def validPoW(ht, cd):
    return ht.getHash() < cd.unpackedTarget

def ghash(msg):
    ''' This is the hash function that should be used EVERYWHERE in GPDHT.
    Currently defined to be SHA3.
    As always, should return a BANT '''
    s = hashlib.sha3_256()
    s.update(bytes(msg))
    return int.from_bytes(s.digest(), 'big')



def packTarget(unpackedTarget):
    # TODO : test
    pad = 32 - len(unpackedTarget)
    while unpackedTarget[0] == 0:
        pad += 1
        unpackedTarget = unpackedTarget[1:]
    a = unpackedTarget[:3] + bytearray([pad])
    return BANT(a)
    
def unpackTarget(packedTarget):
    # TODO : test
    packedTarget = bytes(packedTarget)
    pad = packedTarget[3]
    sigfigs = packedTarget[:3]
    rt = ZERO*pad + sigfigs + ZERO*(32-3-pad)
    return BANT(int(hexlify(rt),16))


#=========================
# CHAIN
#=========================

class Chain(object):
    ''' Holds a PoW chain and can answer queries '''
    # initial conditions must be updated when Chaindata structure updated
    
    def __init__(self, chainVars, genesisBlock=None, db=None, cryptonet=None):
        self.initialized = False
        self.cryptonet = cryptonet
        self._Block = self.cryptonet._Block
        self.head = None
        self.db = db
        self.miner = None
        self.blocks = set()
        self.blockhashes = set()
        
        self.genesisBlock = None
        if genesisBlock != None: self.setGenesis(genesisBlock)
        
    def restartMiner(self):
        if self.miner != None:
            self.miner.restart()
        
    def setMiner(self, miner):
        self.miner = miner
    
    def hash(self, message):
        return ghash(message)
        
    def setGenesis(self, block):
        if self.genesisBlock == None:
            block.assertValidity(self)
            
            self.genesisBlock = block
            self.head = block
            
            self.addBlock(block)
        else:
            raise ChainError('genesis block already known: %s' % self.genesisBlock)
        
    # added sigmadiff stuff, need to test
    def addBlock(self, block):
        if self.hasBlock(block): return
        
        if block.betterThan(self.head):
            self.head = block
            debug('chain: new head %d, hash: %064x' % (block.height, block.getHash()))
        
        self.db.setEntry(block.getHash(), block)
        self.db.setAncestors(block)
        self.blocks.add(block)
        self.blockhashes.add(block.getHash())
        
        
        if self.initialized == False:
            self.initialized = True
        
        debug('added block %d, hash: %064x' % (block.height, block.getHash()))
        
        self.restartMiner()
        
    def getBlock(self, blockhash):
        return self.db.getEntry(blockhash)
        
    def hasBlock(self, block):
        return block in self.blocks
          
    def hasBlockhash(self, blockhash):
        return blockhash in self.blockhashes
    
    def validAlert(self, alert):
        # TODO : not in PoC, probably not in GPDHTChain either
        # TODO : return True if valid alert
        pass
        
    
    def getSuccessors(self, blocks, stop):
        # TODO : not in PoC
        # TODO : Probably won't be used with new blockchain struct
        # TODO : find HCB and then some successors until stop or max num
        #return [self.db.getSuccessors(b) for b in blocks]
        pass
        
    def getHeight(self):
        return self.head.height
        
    def getTopBlock(self):
        return self.head
        
    def getAncestors(self, start):
        return self.db.getAncestors(start)
        
    def loadChain(self):
        # TODO : load chainstate from database
        pass
        #self.db.getSuccessors(self.genesisHash)
    
    def learnOfDB(self, db):
        self.db = db
        self.loadChain()

