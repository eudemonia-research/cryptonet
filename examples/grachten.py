#!/usr/bin/env python3

import time, argparse

from encodium import *

from cryptonet import Cryptonet
from cryptonet.miner import Miner
from cryptonet.datastructs import ChainVars
from cryptonet.datastructs import MerkleTree
from cryptonet.errors import ValidationError
from cryptonet.utilities import global_hash
from cryptonet.debug import debug


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
chain_vars.genesis_binary = None
chain_vars.genesis_binary = b'\x01O\x01!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB\t\x00\xabT\xa9\x8c\xdcgs\xf46\x01\x01\x01\x01\x00 \x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x02\x01\x00\x04SG\x9c\x93\x01\x00\x01\x00\x03\x01\x01\x00\x01\x01'
chain_vars.address = (config['host'], config['port'])
chain_vars.mine = args.mine


grachten = Cryptonet(chain_vars)

class GrachtenUncle(Field):
    pass

class GrachtenHeader(Field):
    
    DEFAULT_TARGET = 2**248-1
    _TARGET1 = 2**256-1
    RETARGET_PERIOD = 16
    BLOCKS_PER_DAY = 1440
    timeint = lambda : int(time.time())
        
    def init(self):
        self.previous_blocks_with_height = [(self.height - 2**i, self.previous_blocks[i]) for i in range(len(self.previous_blocks))]
        
    def fields():
        version = Integer(default=1, length=4)
        height = Integer(default=0, length=4)
        target = Integer(default=GrachtenHeader.DEFAULT_TARGET, length=32)
        sigma_diff = Integer(default=0x100)
        timestamp = Integer(default=GrachtenHeader.timeint, length=5)
        votes = Integer(default=0, length=1)
        uncles_mr = Integer(default=0, length=32)
        previous_blocks = List(Integer(), default=[0])
        
    def get_hash(self):
        temp_cont = [
            self.version.to_bytes(4, 'big'),
            self.height.to_bytes(4, 'big'),
            self.target.to_bytes(32, 'big'),
            self.sigma_diff.to_bytes(32, 'big'),
            self.timestamp.to_bytes(5, 'big'),
            self.votes.to_bytes(1, 'big'),
            self.uncles_mr.to_bytes(32, 'big'),
        ]
        temp_cont.extend( [i.to_bytes(32, 'big') for i in self.previous_blocks] )
        return global_hash(b''.join(temp_cont))
        
    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError(message)
        
    def assert_internal_consistency(self):
        self.assert_true(self.timestamp < time.time() + 60*15, 'new block cannot be more than 15 minutes ahead of present')
        self.assert_true(self.uncles_mr == 0, 'uncles must be zeroed')
        self.assert_true(self.uncles_mr <= 2**256-1, 'uncles must be no more than 32 bytes long')
        self.assert_true(self.version == 1, 'version must be equal to 1, is %x' % self.version)
        
    def assert_validity(self, chain):
        self.assert_internal_consistency()
        self.assert_true( self.version == 1, 'version must be equal to 1' )
        if chain.initialized:
            self.assert_true( self.previous_blocks == chain.get_ancestors(self.previous_blocks[0]), 'previous_blocks should match predicted ancestors' )
            self.assert_true( self.height == chain.get_block(self.previous_blocks[0]).height + 1, 'height requirement, prevheight += 1' )
            self.assert_true( self.sigma_diff == GrachtenHeader.calc_sigma_diff(self, chain.get_block(self.previous_blocks[0])), 'sigma_diff as expected' )
        else:
            self.assert_true( self.uncles_mr == 0, 'genesis requires zeroed uncles_mr' )
            self.assert_true( self.previous_blocks[0] == 0, 'genesis requires zeroed previous_block' )
            self.assert_true( len(self.previous_blocks) == 1, 'genesis can have only one previous_block' )
            self.assert_true( self.sigma_diff == self.calc_sigma_diff(self), 'genesis sigma_diff requirement' )
        
    def target_to_diff(target):
        return GrachtenHeader._TARGET1 // target
        
    # need to test
    def calc_sigma_diff(header, previous_block=None):
        ''' given header, calculate the sigma_diff '''
        if header.previous_blocks[0] == 0: prevsigma_diff = 0
        else: prevsigma_diff = previous_block.header.sigma_diff
        return prevsigma_diff + GrachtenHeader.target_to_diff(header.target)
        
    def calc_expected_target(header, previous_block, chain):
        ''' given a header and previous_block, calculate the expected target '''
        if header.previous_blocks[0] == 0: return GrachtenHeader.DEFAULT_TARGET
        if header.height % GrachtenHeader.RETARGET_PERIOD != 0: return previous_block.header.target
        
        old_ancestor = chain.get_block(header.previous_blocks[(GrachtenHeader.RETARGET_PERIOD-1).bit_length()])
        timedelta = header.timestamp - old_ancestor.header.timestamp
        expected_timedelta = 60 * 60 * 24 * GrachtenHeader.RETARGET_PERIOD // GrachtenHeader.BLOCKS_PER_DAY
        
        if timedelta < expected_timedelta // 4: timedelta = expected_timedelta // 4
        if timedelta > expected_timedelta * 4: timedelta = expected_timedelta * 4
        
        new_target = previous_block.header.target * timedelta // expected_timedelta
        debug('New Target Calculated: %064x, height: %d' % (new_target, header.height))
        return new_target

    @staticmethod
    def header_template(chain, previous_block):
        new_grachten_header = GrachtenHeader.make(height = chain.head.height + 1, previous_blocks = chain.db.get_ancestors(chain.head.get_hash()))
        new_grachten_header.target = GrachtenHeader.calc_expected_target(new_grachten_header, previous_block, chain)
        new_grachten_header.sigma_diff = GrachtenHeader.calc_sigma_diff(new_grachten_header, previous_block)
        return new_grachten_header
        
    def get_candidate(self, chain, previous_block):
        ''' should return a candidate header that builds on this one '''
        return self.header_template(chain, previous_block)
        
    def valid_proof_of_work(self, block):
        return block.get_hash() < self.target
        
@grachten.block
class GrachtenBlock(Field):   
    def init(self):
        self.merkle_tree = MerkleTree.make(leaves = self.leaves)
        self.parent_hash = self.header.previous_blocks[0]
        self.height = self.header.height
         
    def fields():
        leaves = List(Integer(default=0, length=32), default=[])
        header = GrachtenHeader()
        uncles = List(GrachtenUncle(), default=[])
        
    def __hash__(self):
        return self.get_hash()
        
    def get_hash(self):
        return int(self.merkle_tree.get_hash())
        
    def valid_proof_of_work(self):
        return self.header.valid_proof_of_work(self)
        
    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError(message)
            
    def assert_internal_consistency(self):
        ''' This should fail if the block could never be valid - no reference to chain possible '''
        self.header.assert_internal_consistency()
        self.assert_true( self.valid_proof_of_work(), 'PoW must validate against header: %064x' % self.get_hash() )
        #debug('block: AssertInternalConsistency', self.tree.leaves)
        self.assert_true( self.header.get_hash() == self.leaves[1], 'GrachtenHeader hash must be in pos 1 of tree, %s %064x' % (self.leaves, self.header.get_hash()))
        
    def assert_validity(self, chain):
        ''' This should fail only when the block cannot be fully validated against our chain.
        :param chain: the Blockchain this block is being validated against
        '''
        self.assert_internal_consistency()
        self.header.assert_validity(chain)
        if chain.initialized:
            self.assert_true( chain.has_block_hash(self.parent_hash), 'parent must exist' )
            self.assert_true( chain.genesis_block.header.get_hash() == self.merkle_tree.leaves[0], 'genesis block hash location requirement' )
        else:
            self.assert_true( self.parent_hash == 0, 'parent must be zeroed' )
            self.assert_true( self.merkle_tree.leaves[0] == self.merkle_tree.leaves[1] and self.merkle_tree.leaves[0] == self.header.get_hash(), 'genesis header hash requirement' )
    
    def better_than(self, other):
        return self.header.sigma_diff > other.header.sigma_diff
        
    def related_blocks(self):
        ''' if any block hashes known and should seek, add here.
        Should be in list of tuples of (height, block_hash) '''
        return self.header.previous_blocks_with_height
        
    def increment_nonce(self):
        nonce = self.merkle_tree.leaves[-1] + 1
        self.leaves = self.merkle_tree.leaves[:-1] + [nonce]
        self.merkle_tree = MerkleTree.make(leaves = self.leaves)
        
    def get_candidate(self, chain):
        ''' return a block object that is a candidate for the next block '''
        new_grachten_header = self.header.get_candidate(chain, self)
        new_tree_list = [self.merkle_tree.leaves[0], new_grachten_header.get_hash(), global_hash(b'some_message'), global_hash(b'another_message?')]
        return GrachtenBlock.make(leaves=new_tree_list, header=new_grachten_header, uncles=[])

    def reorganisation(self, new_head, chain):
        pass


def make_genesis():
    """ General way to make a genesis block. """
    genesis_header = GrachtenHeader.make()
    genesis_block = GrachtenBlock.make(leaves=[genesis_header.get_hash(), genesis_header.get_hash(), int.from_bytes(b'some message', 'big')], header=genesis_header)
    m = Miner(grachten.chain, grachten.seek_n_build)
    m.mine(genesis_block)


if __name__ == "__main__":
    grachten.run()
