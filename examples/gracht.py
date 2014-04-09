#!/usr/bin/env python3

import time

from cryptonet import Cryptonet
from cryptonet.datastructs import ChainVars
from cryptonet.datastructs import MerkleTree
from cryptonet.errors import ValidationError
from cryptonet import rlp

from cryptonet.gpdht import *

chainVars = ChainVars()
chainVars.seeds = [('xk.io',32555)]
chainVars.genesisBinary = b"\xf8\xe7\xf8\x84\xa0T(\xe1y\x8an\x84\x1a\x9c\xd8\x1a0\xec\x8e\x8eh\xa5y\xfa~_K\x81\x15+\x95pR\xd7=\xdd\x98\xa0T(\xe1y\x8an\x84\x1a\x9c\xd8\x1a0\xec\x8e\x8eh\xa5y\xfa~_K\x81\x15+\x95pR\xd7=\xdd\x98\xa0\x19?e\xc9\xe4\xe7\xb8\xb9-\x08\'\x844O\xad\x9es$\x99\xbc\x1e|c\xf8\x9a\xe6\x182\xcc\xcb|\xcc\xa0\x19?e\xc9\xe4\xe7\xb8\xb9-\x08\'\x844O\xad\x9es$\x99\xbc\x1e|c\xf8\x9a\xe6\x182\xcc\xcb\x7fP\xf8^\x82\x00\x01\x84\x00\x00\x00\x00\x84\xff\xff\xff\x01\x82\x01\x00\x86\x00\x00SA3\xe0\x84\x00\x00\x00\x01\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0"

gracht = Cryptonet(chainVars)


class Header(object):
    _target1 = BANT(2**256-1)
    retargetPeriod = 64
    blocksPerDay = 1440
    _initialConditions = [
            BANT(1,padTo=2), # version
            BANT(0,padTo=4), # height
            BANT(b'\xff\xff\xff\x01'), # target
            BANT(b'\x01\x00'), # sigmadiff
            BANT(int(time.time()), padTo=6), # timestamp
            BANT(1, padTo=4), # votes
            BANT(bytearray(32)), # uncles
            BANT(bytearray(32)), # prevblock
        ]
    def __init__(self, hl, uncles):
        self.uncles = uncles
        self.rawlist = hl
        
        self.map = ["version", "height", "target", "sigmadiff", "timestamp", "votes", "uncles", "prevblocks"] # prev1, 2, 4, 8, ... appended here
        self.map = dict([(title,n) for n,title in enumerate(self.map)])
        
        self.version = hl[self.map['version']]
        self.height = hl[self.map['height']]
        self.target = hl[self.map['target']]
        self.sigmadiff = hl[self.map['sigmadiff']]
        self.timestamp = hl[self.map['timestamp']]
        self.votes = hl[self.map['votes']]
        self.unclesMR = hl[self.map['uncles']]
        # there is an ancestry summary here
        self.prevblocks = hl[self.map['prevblocks']:]
        self.prevblocksWithHeight = [(int(self.height) - 2**i, self.prevblocks[i]) for i in range(len(self.prevblocks))]
        self.unpackedTarget = BANT(self.unpackTarget())
        self.hash = ghash(rlp.serialize(hl))
        
    def getHash(self):
        return self.hash
        
    def assertTrue(self, condition, message):
        if not condition:
            raise ValidationError(message)
        
    def assertInternalConsistency(self):
        self.assertTrue( self.timestamp < time.time() + 60*15, 'new block cannot be more than 15 minutes ahead of present' )
        self.assertTrue( self.unclesMR == 0, 'uncles must be zeroed' )
        self.assertTrue( len(self.unclesMR) == 32, 'uncles must be 32 bytes long' )
        self.assertTrue( self.version == 1, 'version must be equal to 1' )
        
    def assertValidity(self, chain):
        self.assertInternalConsistency()
        if chain.initialized:
            #parentBlock = chain.getBlock(self.prevblocks[0])
            # ancestors
            self.assertTrue( self.prevblocks == chain.getAncestors(self.prevblocks[0]), 'prevblocks should match predicted ancestors' )
            # height
            self.assertTrue( self.height == chain.getBlock(self.prevblocks[0]).height + 1, 'height requirement, prevheight += 1' )
            # sigmadiff
        else:                
            assert int(self.unclesMR) == 0
            assert int(self.prevblocks[0]) == 0
            assert len(self.prevblocks) == 1
            assert int(self.version) == 1
        
        
    # no idea if these work
    def unpackTarget(self):
        packedTarget = self.target[:]
        pad = packedTarget[3]
        sigfigs = packedTarget[:3]
        rt = b'\x00'*int(pad) + bytes(sigfigs) + b'\x00'*(32-3-int(pad))
        return BANT(int(hexlify(rt),16))
        
    # no idea if these work
    def packTarget(self, unpackedTarget):
        unpackedTarget = unpackedTarget[:]
        pad = 32 - len(unpackedTarget)
        while unpackedTarget[0] == 0:
            pad += 1
            unpackedTarget = unpackedTarget[1:]
        a = unpackedTarget[:3] + bytearray([pad])
        return a
        
    def targetToDiff(self, target):
        if isinstance(target, BANT): return self._target1 // unpackTarget(target)
        return self._target1 // target
        
        
    # need to test
    def calcSigmadiff(self, cd):
        ''' given chaindata, calculate the sigmadiff '''
        # TODO : test
        prevblockhash = cd.prevblocks[0]
        if prevblockhash == 0:
            prevsigmadiff = BANT(0)
        else:
            prevblocktree = self.db.getEntry(prevblockhash)
            prevChaindata = Chaindata(self.db.getEntry(prevblocktree[1])) # each GPDHT block has 2nd entry as Chaindata hash
            prevsigmadiff = prevChaindata.sigmadiff
        diff = self.targetToDiff(cd.target)
        sigmadiff = prevsigmadiff + diff
        return sigmadiff
        
    def calcExpectedTarget(self, cd):
        ''' given chaindata, calculate the expected target '''
        if cd.prevblocks[0] == 0: return self._initialConditions[CDM['target']]
        parentTree = self.db.getEntry(cd.prevblocks[0])
        parentChaindata = Chaindata(self.db.getEntry(parentTree[1]))
        
        if cd.height % self.retargetPeriod != 0:
            return parentChaindata.target
        
        oldAncestorTree = self.db.getEntry(cd.prevblocks[(self.retargetPeriod-1).bit_length()])
        oldAncestorChaindata = Chaindata(self.db.getEntry(oldAncestorTree[1]))
        timedelta = cd.timestamp - oldAncestorChaindata.timestamp
        #print(cd.timestamp.hex(), oldAncestorChaindata.timestamp.hex())
        expectedTimedelta = 60 * 60 * 24 * self.retargetPeriod // self.blocksPerDay
        
        print(timedelta.__int__(), expectedTimedelta)
        
        if timedelta < expectedTimedelta // 4: timedelta = expectedTimedelta // 4
        if timedelta > expectedTimedelta * 4: timedelta = expectedTimedelta * 4
        
        newTarget = packTarget(parentChaindata.unpackedTarget * timedelta // expectedTimedelta)
        print('New Target Calculated: %s, height: %d' % (newTarget.hex(), cd.height)   )
        return newTarget
        
        
    def headerTemplate(self):
        # TODO : do a real block template here
        ret = self._initialConditions[:]
        if self.initComplete:
            # replace target with correct target
            # set height
            ret[CDM['height']] = self.headChaindata.height + 1
            # set prevblocks
            ancs = self.db.getAncestors(self.head.getHash())
            ret[CDM['prevblock']] = ancs[0]
            ret.extend(ancs[1:])
            # set timestamp
            ret[CDM['timestamp']] = BANT(int(time.time()))
            # set votes
            # set uncles
            # set target
            ret[CDM['target']] = self.calcExpectedTarget(Chaindata(ret))
            # set sigmadiff
            ret[CDM['sigmadiff']] = self.headChaindata.sigmadiff + self.targetToDiff(ret[CDM['target']])
        return Chaindata(ret)
        
class Uncles:
    def __init__(self, ul):
        self._uncles = []
        for uncle in ul:
            # TODO : validate Chaindata in hashtree
            self._uncles.append( HashTree(uncle[UM['hashtree']]) )
        # commented for now
        #self._tree = HashTree(self._uncles)
        self.rawlist = []
    
    #def getHash():
        #return self._tree.getHash()            


@gracht.block
class Block(object):
    def __init__(self, rawlist=None):
        if rawlist != None: self.setFromRawlist(rawlist)
        
    def __eq__(self, other):
        return self.getHash() == other.getHash()
        
    def __hash__(self):
        return int(self.getHash())
        
    def setFromRawlist(self, rawlist):
        self.tree = MerkleTree(rawlist[0])
        self.header = Header(rawlist[1], Uncles(rawlist[2]))
        
        self.height = self.header.height
        self.parenthash = self.header.prevblocks[0]
        
    def serialize(self):
        return rlp.serialize([self.tree.leaves, self.header.rawlist, self.header.uncles.rawlist])
        
    def deserialize(self, serialized):
        self.setFromRawlist(rlp.deserialize(serialized))
        return self
        
    def getHash(self):
        return self.tree.getHash()
        
    def validPoW(self):
        return self.getHash() < self.header.unpackedTarget
        
    def assertTrue(self, condition, message):
        if not condition:
            raise ValidationError(message)
            
    def assertInternalConsistency(self):
        ''' This should fail if the block could never be valid - no 
        reference to chain possible '''
        self.header.assertInternalConsistency()
        # valid PoW
        self.assertTrue( self.validPoW(), 'PoW must validate against header' )
        # header hash location requirement
        
    def assertValidity(self, chain):
        ''' This should fail only when the block cannot be fully validated 
        against our chain. '''
        self.assertInternalConsistency()
        self.header.assertValidity(chain)
        # we have parent
        if chain.initialized:
            self.assertTrue( chain.hasBlockhash(self.parenthash), 'parent must exist' )
            # genesis block location requirement
            self.assertTrue( chain.genesisBlock.header.getHash() == self.tree.pos(0), 'genesis block hash location requirement' )        
        else:
            self.assertTrue( self.parenthash == 0 and len(self.parenthash) == 32, 'parent must be zeroed' )
            self.assertTrue( self.tree.pos(0) == self.tree.pos(1) and self.tree.pos(0) == self.header.getHash(), 'genesis header hash requirement' )
    def betterThan(self, other):
        return self.header.sigmadiff > other.header.sigmadiff
        
    def relatedBlocks(self):
        ''' if any block hashes known and should seek, add here.
        Should be in list of tuples of (height, blockhash) '''
        
        #print(self.height.hex(), [(int(self.height) - 2**i, self.header.prevblocks[i]) for i in range(len(self.header.prevblocks))])
        
        return [(int(self.height) - 2**i, self.header.prevblocks[i]) for i in range(len(self.header.prevblocks))]
        
        
'''tree = [
    BANT("5428e1798a6e841a9cd81a30ec8e8e68a579fa7e5f4b81152b957052d73ddd98", True),
    BANT("5428e1798a6e841a9cd81a30ec8e8e68a579fa7e5f4b81152b957052d73ddd98", True),
    BANT("193f65c9e4e7b8b92d082784344fad9e732499bc1e7c63f89ae61832cccb7ccc", True),
    BANT("193f65c9e4e7b8b92d082784344fad9e732499bc1e7c63f89ae61832cccb7f50", True)
    ]
h =  [
    BANT("0001", True),
    BANT("00000000", True),
    BANT("ffffff01", True),
    BANT("0100", True),
    BANT("0000534133e0", True),
    BANT("00000001", True),
    BANT("0000000000000000000000000000000000000000000000000000000000000000", True),
    BANT("0000000000000000000000000000000000000000000000000000000000000000", True)]
    
a = Block([tree,h,[]])
print(a.serialize().raw())'''
    

gracht.run()
