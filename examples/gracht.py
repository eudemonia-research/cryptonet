#!/usr/bin/env python3

import time, argparse

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.datastructs import MerkleTree
from cryptonet.errors import ValidationError
from cryptonet.gpdht import *
from cryptonet import rlp

from encodium import *

chainVars = ChainVars()


config = {
    'host': '0.0.0.0',
    'port': 32555,
    'networkdebug': False
}

parser = argparse.ArgumentParser()
parser.add_argument('-port', nargs=1, default=32555, type=int, help='port for node to bind to')
parser.add_argument('-addnode', nargs=1, default='', type=str, help='node to connect to non-exclusively. Format xx.xx.xx.xx:yyyy')
parser.add_argument('-genesis', nargs=1, default=BANT(), type=BANT, help='genesis block in hex')
parser.add_argument('-mine', action='store_true')
parser.add_argument('-networkdebug', action='store_true')
args = parser.parse_args()

config['port'] = args.port
if isinstance(args.port, list): config['port'] = args.port[0]
seeds = []
if isinstance(args.addnode, list) and args.addnode[0] != '':
    h,p = args.addnode[0].split(':')
    seeds.append((h,p))
    
# bootstrap while testing
#seeds.append(('xk.io',32555))


chainVars.seeds = seeds
chainVars.genesisBinary = None
chainVars.genesisBinary = b'\x01O\x01!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB\t\x00\xabT\xa9\x8c\xdcgs\xf46\x01\x01\x01\x01\x00 \x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x02\x01\x00\x04SG\x9c\x93\x01\x00\x01\x00\x03\x01\x01\x00\x01\x01'
chainVars.address = (config['host'], config['port'])
chainVars.mine = args.mine


gracht = Cryptonet(chainVars)

class Uncle(Field):
    pass

class Header(Field):
    
    DEFAULT_TARGET = 2**248-1
    _TARGET1 = 2**256-1
    RETARGET_PERIOD = 64
    BLOCKS_PER_DAY = 1440
    timeint = lambda : int(time.time())
    
    '''_initialConditions = [
            BANT(1,padTo=2), # version
            BANT(0,padTo=4), # height
            BANT(b'\xff\xff\xff\x01'), # target
            BANT(b'\x01\x00'), # sigmadiff
            BANT(int(time.time()), padTo=6), # timestamp
            BANT(1, padTo=4), # votes
            BANT(bytearray(32)), # uncles
            BANT(bytearray(32)), # prevblock
        ]'''
        
    def init(self):
        #self.prevblocksWithHeight = [(self.height - 2**i, self.prevblocks[i]) for i in range(len(self.prevblocks))]
        pass
    
    def fields():
        version = Integer(default=1, length=4)
        height = Integer(default=0, length=4)
        target = Integer(default=Header.DEFAULT_TARGET, length=32)
        sigmadiff = Integer(default=0x100)
        timestamp = Integer(default=Header.timeint, length=5)
        votes = Integer(default=0, length=1)
        unclesMR = Integer(default=0, length=32)
        prevblocks = List(Integer(), default=[0])
        
    def getHash(self):
        tempCont = [
            self.version.to_bytes(4, 'big'),
            self.height.to_bytes(4, 'big'),
            self.target.to_bytes(32, 'big'),
            self.sigmadiff.to_bytes(32, 'big'),
            self.timestamp.to_bytes(5, 'big'),
            self.votes.to_bytes(1, 'big'),
            self.unclesMR.to_bytes(32, 'big'),
        ]
        tempCont.extend( [i.to_bytes(32, 'big') for i in self.prevblocks] )
        return ghash(b''.join(tempCont))
        
    def assertTrue(self, condition, message):
        if not condition:
            raise ValidationError(message)
        
    def assertInternalConsistency(self):
        self.assertTrue( self.timestamp < time.time() + 60*15, 'new block cannot be more than 15 minutes ahead of present' )
        self.assertTrue( self.unclesMR == 0, 'uncles must be zeroed' )
        self.assertTrue( self.unclesMR <= 2**256-1, 'uncles must be no more than 32 bytes long' )
        self.assertTrue( self.version == 1, 'version must be equal to 1' )
        
    def assertValidity(self, chain):
        self.assertInternalConsistency()
        self.assertTrue( self.version == 1, 'version must be equal to 1' )
        if chain.initialized:
            self.assertTrue( self.prevblocks == chain.getAncestors(self.prevblocks[0]), 'prevblocks should match predicted ancestors' )
            self.assertTrue( self.height == chain.getBlock(self.prevblocks[0]).height + 1, 'height requirement, prevheight += 1' )
            self.assertTrue( self.sigmadiff == self.calcSigmadiff(self, chain.getBlock(self.prevblocks[0])), 'sigmadiff as expected' )
        else:
            self.assertTrue( self.unclesMR == 0, 'genesis requires zeroed unclesMR' )
            self.assertTrue( self.prevblocks[0] == 0, 'genesis requires zeroed prevblock' )
            self.assertTrue( len(self.prevblocks) == 1, 'genesis can have only one prevblock' )
            self.assertTrue( self.sigmadiff == self.calcSigmadiff(self), 'genesis sigmadiff requirement' )
        
    def targetToDiff(target):
        return Header._TARGET1 // target
        
    # need to test
    def calcSigmadiff(header, prevblock=None):
        ''' given header, calculate the sigmadiff '''
        if header.prevblocks[0] == 0: prevsigmadiff = 0
        else: prevsigmadiff = prevblock.header.sigmadiff
        debug(type(prevsigmadiff), type(header.target))
        return prevsigmadiff + Header.targetToDiff(header.target)
        
    def calcExpectedTarget(header, chain):
        ''' given a header and prevblock, calculate the expected target '''
        if header.prevblocks[0] == 0: return self.DEFAULT_TARGET
        prevblock = chain.getBlock(header.prevblocks[0])
        if header.height % self.RETARGET_PERIOD != 0: return prevblock.header.target
        
        oldAncestor = chain.getBlock(header.prevblocks[(self.RETARGET_PERIOD-1).bit_length()])
        timedelta = header.timestamp - oldAncestor.header.timestamp
        expectedTimedelta = 60 * 60 * 24 * self.RETARGET_PERIOD // self.BLOCKS_PER_DAY
        
        if timedelta < expectedTimedelta // 4: timedelta = expectedTimedelta // 4
        if timedelta > expectedTimedelta * 4: timedelta = expectedTimedelta * 4
        
        newTarget = prevblock.header.target * timedelta // expectedTimedelta
        debug('New Target Calculated: %04x, height: %d' % (newTarget, header.height))
        return newTarget
        
    def headerTemplate(chain, prevblock):
        newHeader = Header.make(height = chain.head.height + 1, prevblocks = chain.db.getAncestors(chain.head.getHash()))
        newHeader.target = Header.calcExpectedTarget(newHeader, chain)
        newHeader.sigmadiff = Header.calcSigmadiff(newHeader, prevblock)
        '''# TODO : do a real block template here
        ret = self._initialConditions[:]
        # set height
        ret[self.map['height']] = chain.head.height + 1
        # set prevblocks
        ancs = chain.db.getAncestors(chain.head.getHash())
        ret[self.map['prevblocks']] = ancs[0]
        ret.extend(ancs[1:])
        # set timestamp
        ret[self.map['timestamp']] = BANT(int(time.time()))
        # set votes
        # set uncles
        # set target
        ret[self.map['target']] = self.calcExpectedTarget(Header(ret, Uncles([])), chain)
        # set sigmadiff
        ret[self.map['sigmadiff']] = chain.head.header.sigmadiff + self.targetToDiff(ret[self.map['target']])'''
        return newHeader
        
    def getCandidate(self, chain, prevblock):
        ''' should return a candidate header that builds on this one '''
        return self.headerTemplate(chain, prevblock)
        
@gracht.block
class Block(Field):   
    def init(self):
        self.merkletree = MerkleTree.make(leaves = self.leaves)
        self.parenthash = self.header.prevblocks[0]
        self.height = self.header.height
         
    def fields():
        leaves = List(Integer(default=0, length=32), default=[])
        header = Header()
        uncles = List(Uncle(), default=[])
        
    def __hash__(self):
        return self.getHash()
        
    def getHash(self):
        return int(self.merkletree.getHash())
        
    def validPoW(self):
        return self.getHash() < self.header.target
        
    def assertTrue(self, condition, message):
        if not condition:
            raise ValidationError(message)
            
    def assertInternalConsistency(self):
        ''' This should fail if the block could never be valid - no reference to chain possible '''
        self.header.assertInternalConsistency()
        self.assertTrue( self.validPoW(), 'PoW must validate against header: %064x' % self.getHash() )
        #debug('block: AssertInternalConsistency', self.tree.leaves)
        self.assertTrue( self.header.getHash() == self.leaves[1], 'Header hash must be in pos 1 of tree, %s %064x' % (self.leaves, self.header.getHash()))
        
    def assertValidity(self, chain):
        ''' This should fail only when the block cannot be fully validated against our chain. '''
        self.assertInternalConsistency()
        self.header.assertValidity(chain)
        if chain.initialized:
            self.assertTrue( chain.hasBlockhash(self.parenthash), 'parent must exist' )
            self.assertTrue( chain.genesisBlock.header.getHash() == self.merkletree.leaves[0], 'genesis block hash location requirement' )        
        else:
            self.assertTrue( self.parenthash == 0, 'parent must be zeroed' )
            self.assertTrue( self.merkletree.leaves[0] == self.merkletree.leaves[1] and self.merkletree.leaves[0] == self.header.getHash(), 'genesis header hash requirement' )
    
    def betterThan(self, other):
        return self.header.sigmadiff > other.header.sigmadiff
        
    def relatedBlocks(self):
        ''' if any block hashes known and should seek, add here.
        Should be in list of tuples of (height, blockhash) '''
        return self.header.prevblocksWithHeight
        
    def incrementNonce(self):
        nonce = self.merkletree.leaves[-1] + 1
        self.leaves = self.merkletree.leaves[:-1] + [nonce]
        self.merkletree = MerkleTree.make(leaves = self.leaves)
        
    def getCandidate(self, chain):
        ''' return a block object that is a candidate for the next block '''
        newHeader = self.header.getCandidate(chain, self)
        newTreeList = [self.tree.leaves[0], newHeader.getHash(), ghash(b'some_message'), ghash(b'another_message?')]
        return Block.make(tree=newTreeList, header=newHeader, uncles=[])
        
        
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

def makeGenesis():
    genH = Header.make()
    genB = Block.make(leaves=[genH.getHash(), genH.getHash(), 12345678900987654321], header=genH)
    m = Miner(gracht.chain, gracht.seekNBuild)
    m.mine(genB)

gracht.run()
