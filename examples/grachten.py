#!/usr/bin/env python3

import time, argparse

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.datastructs import MerkleTree
from cryptonet.errors import ValidationError
from cryptonet.gpdht import *

from encodium import *

chain_vars = ChainVars()


config = {
    'host': '0.0.0.0',
    'port': 32555,
    'network_debug': False
}

parser = argparse.ArgumentParser()
parser.add_argument('-port', nargs=1, default=32555, type=int, help='port for node to bind to')
parser.add_argument('-addnode', nargs=1, default=b'', type=str, help='node to connect to non-exclusively. Format xx.xx.xx.xx:yyyy')
parser.add_argument('-genesis', nargs=1, default=b'', type=bytes, help='genesis block in hex')
parser.add_argument('-mine', action='store_true')
parser.add_argument('-network_debug', action='store_true')
args = parser.parse_args()

config['port'] = args.port
if isinstance(args.port, list): config['port'] = args.port[0]
seeds = []
if isinstance(args.addnode, list) and args.addnode[0] != '':
    h,p = args.addnode[0].split(':')
    seeds.append((h,p))
    
# bootstrap while testing
#seeds.append(('xk.io',32555))


chain_vars.seeds = seeds
chain_vars.genesisBinary = None
chain_vars.genesisBinary = b'\x01O\x01!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB\t\x00\xabT\xa9\x8c\xdcgs\xf46\x01\x01\x01\x01\x00 \x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x02\x01\x00\x04SG\x9c\x93\x01\x00\x01\x00\x03\x01\x01\x00\x01\x01'
chain_vars.address = (config['host'], config['port'])
chain_vars.mine = args.mine


gracht = Cryptonet(chain_vars)

class GrachtUncle(Field):
    pass

class GrachtHeader(Field):
    
    DEFAULT_TARGET = 2**248-1
    _TARGET1 = 2**256-1
    RETARGET_PERIOD = 16
    BLOCKS_PER_DAY = 1440
    timeint = lambda : int(time.time())
        
    def init(self):
        self.prevblocksWithHeight = [(self.height - 2**i, self.prevblocks[i]) for i in range(len(self.prevblocks))]
        
    def fields():
        version = Integer(default=1, length=4)
        height = Integer(default=0, length=4)
        target = Integer(default=GrachtHeader.DEFAULT_TARGET, length=32)
        sigmadiff = Integer(default=0x100)
        timestamp = Integer(default=GrachtHeader.timeint, length=5)
        votes = Integer(default=0, length=1)
        unclesMR = Integer(default=0, length=32)
        prevblocks = List(Integer(), default=[0])
        
    def get_hash(self):
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
        
    def assert_internal_consistency(self):
        self.assertTrue( self.timestamp < time.time() + 60*15, 'new block cannot be more than 15 minutes ahead of present' )
        self.assertTrue( self.unclesMR == 0, 'uncles must be zeroed' )
        self.assertTrue( self.unclesMR <= 2**256-1, 'uncles must be no more than 32 bytes long' )
        self.assertTrue( self.version == 1, 'version must be equal to 1' )
        
    def assertValidity(self, chain):
        self.assert_internal_consistency()
        self.assertTrue( self.version == 1, 'version must be equal to 1' )
        if chain.initialized:
            self.assertTrue( self.prevblocks == chain.getAncestors(self.prevblocks[0]), 'prevblocks should match predicted ancestors' )
            self.assertTrue( self.height == chain.get_block(self.prevblocks[0]).height + 1, 'height requirement, prevheight += 1' )
            self.assertTrue( self.sigmadiff == GrachtHeader.calcSigmadiff(self, chain.get_block(self.prevblocks[0])), 'sigmadiff as expected' )
        else:
            self.assertTrue( self.unclesMR == 0, 'genesis requires zeroed unclesMR' )
            self.assertTrue( self.prevblocks[0] == 0, 'genesis requires zeroed prevblock' )
            self.assertTrue( len(self.prevblocks) == 1, 'genesis can have only one prevblock' )
            self.assertTrue( self.sigmadiff == self.calcSigmadiff(self), 'genesis sigmadiff requirement' )
        
    def targetToDiff(target):
        return GrachtHeader._TARGET1 // target
        
    # need to test
    def calcSigmadiff(header, prevblock=None):
        ''' given header, calculate the sigmadiff '''
        if header.prevblocks[0] == 0: prevsigmadiff = 0
        else: prevsigmadiff = prevblock.header.sigmadiff
        return prevsigmadiff + GrachtHeader.targetToDiff(header.target)
        
    def calcExpectedTarget(header, prevblock, chain):
        ''' given a header and prevblock, calculate the expected target '''
        if header.prevblocks[0] == 0: return GrachtHeader.DEFAULT_TARGET
        if header.height % GrachtHeader.RETARGET_PERIOD != 0: return prevblock.header.target
        
        oldAncestor = chain.get_block(header.prevblocks[(GrachtHeader.RETARGET_PERIOD-1).bit_length()])
        timedelta = header.timestamp - oldAncestor.header.timestamp
        expectedTimedelta = 60 * 60 * 24 * GrachtHeader.RETARGET_PERIOD // GrachtHeader.BLOCKS_PER_DAY
        
        if timedelta < expectedTimedelta // 4: timedelta = expectedTimedelta // 4
        if timedelta > expectedTimedelta * 4: timedelta = expectedTimedelta * 4
        
        newTarget = prevblock.header.target * timedelta // expectedTimedelta
        debug('New Target Calculated: %064x, height: %d' % (newTarget, header.height))
        return newTarget
        
    def headerTemplate(chain, prevblock):
        newGrachtHeader = GrachtHeader.make(height = chain.head.height + 1, prevblocks = chain.db.getAncestors(chain.head.get_hash()))
        newGrachtHeader.target = GrachtHeader.calcExpectedTarget(newGrachtHeader, prevblock, chain)
        newGrachtHeader.sigmadiff = GrachtHeader.calcSigmadiff(newGrachtHeader, prevblock)
        return newGrachtHeader
        
    def getCandidate(self, chain, prevblock):
        ''' should return a candidate header that builds on this one '''
        return GrachtHeader.headerTemplate(chain, prevblock)
        
    def validPoW(self):
        return self.get_hash() < self.target
        
@gracht.block
class GrachtBlock(Field):   
    def init(self):
        self.merkletree = MerkleTree.make(leaves = self.leaves)
        self.parenthash = self.header.prevblocks[0]
        self.height = self.header.height
         
    def fields():
        leaves = List(Integer(default=0, length=32), default=[])
        header = GrachtHeader()
        uncles = List(GrachtUncle(), default=[])
        
    def __hash__(self):
        return self.get_hash()
        
    def get_hash(self):
        return int(self.merkletree.get_hash())
        
    def validPoW(self):
        return self.header.validPoW()
        
    def assertTrue(self, condition, message):
        if not condition:
            raise ValidationError(message)
            
    def assert_internal_consistency(self):
        ''' This should fail if the block could never be valid - no reference to chain possible '''
        self.header.assert_internal_consistency()
        self.assertTrue( self.validPoW(), 'PoW must validate against header: %064x' % self.get_hash() )
        #debug('block: AssertInternalConsistency', self.tree.leaves)
        self.assertTrue( self.header.get_hash() == self.leaves[1], 'GrachtHeader hash must be in pos 1 of tree, %s %064x' % (self.leaves, self.header.get_hash()))
        
    def assertValidity(self, chain):
        ''' This should fail only when the block cannot be fully validated against our chain. '''
        self.assert_internal_consistency()
        self.header.assertValidity(chain)
        if chain.initialized:
            self.assertTrue( chain.hasblock_hash(self.parenthash), 'parent must exist' )
            self.assertTrue( chain.genesisBlock.header.get_hash() == self.merkletree.leaves[0], 'genesis block hash location requirement' )        
        else:
            self.assertTrue( self.parenthash == 0, 'parent must be zeroed' )
            self.assertTrue( self.merkletree.leaves[0] == self.merkletree.leaves[1] and self.merkletree.leaves[0] == self.header.get_hash(), 'genesis header hash requirement' )
    
    def betterThan(self, other):
        return self.header.sigmadiff > other.header.sigmadiff
        
    def relatedBlocks(self):
        ''' if any block hashes known and should seek, add here.
        Should be in list of tuples of (height, block_hash) '''
        return self.header.prevblocksWithHeight
        
    def incrementNonce(self):
        nonce = self.merkletree.leaves[-1] + 1
        self.leaves = self.merkletree.leaves[:-1] + [nonce]
        self.merkletree = MerkleTree.make(leaves = self.leaves)
        
    def getCandidate(self, chain):
        ''' return a block object that is a candidate for the next block '''
        newGrachtHeader = self.header.getCandidate(chain, self)
        newTreeList = [self.merkletree.leaves[0], newGrachtHeader.get_hash(), ghash(b'some_message'), ghash(b'another_message?')]
        return GrachtBlock.make(leaves=newTreeList, header=newGrachtHeader, uncles=[])


def makeGenesis():
    genH = GrachtHeader.make()
    genB = GrachtBlock.make(leaves=[genH.get_hash(), genH.get_hash(), int.from_bytes(b'some message', 'big')], header=genH)
    m = Miner(gracht.chain, gracht.seek_n_build)
    m.mine(genB)

gracht.run()
