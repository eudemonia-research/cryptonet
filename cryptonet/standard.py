from encodium import *
#import nacl.signing

from cryptonet.utilities import global_hash

class Signature(Field):

    def fields():
        v = Integer(length=1)
        r = Integer(length=32)
        s = Integer(length=32)

    def to_bytes(self):
        return b''.join([
            self.v.to_bytes(1, 'big'),
            self.r.to_bytes(32, 'big'),
            self.s.to_bytes(32, 'big'),
        ])

    def check_valid_signature(self):
        pass

    def get_hash(self):
        return global_hash(self.to_bytes())

class Tx(Field):
    
    def fields():
        dapp = Bytes()
        value = Integer(length=8)
        fee = Integer(length=4)
        data = List(Bytes(), default=[])
    
    def to_bytes(self):
        return b''.join([
            self.dapp,
            self.value.to_bytes(8, 'big'),
            self.fee.to_bytes(4, 'big'),
            b''.join(self.data)
        ])
    
    def get_hash(self):
        return global_hash(self.to_bytes())
        
        
class SuperTx(Field):
    
    def fields():
        nonce = Integer(length=4)
        txs = List(Tx())
        signature = Signature()
        
    def to_bytes(self):
        return b''.join([
            self.nonce.to_bytes(4, 'big'),
            b''.join([x.to_bytes for x in self.txs]),
            self.signature.to_bytes()
        ])
        
    def get_hash(self):
        return global_hash(self.to_bytes())

        
class Header(Field):
    
    def fields():
        version = Integer(length=2)
        nonce = Integer(length=8) # nonce second to increase work needed for PoW
        timestamp = Integer(length=5)
        target = Integer(length=32)
        sigma_diff = Integer(length=32)
        state_mr = Integer(length=32)
        transaction_mr = Integer(length=32)
        uncles_mr = Integer(length=32, default=0)
        previous_blocks = List(Integer(length=32))
        
    def to_bytes(self):
        return b''.join([
            self.version.to_bytes(2,'big'),
            self.nonce.to_bytes(8, 'big'),
            self.timestamp.to_bytes(5, 'big'),
            self.target.to_bytes(32, 'big'),
            self.sigma_diff.to_bytes(32, 'big'),
            self.state_mr.to_bytes(32, 'big'),
            self.transaction_mr.to_bytes(32, 'big'),
            self.uncles_mr.to_bytes(32, 'big'),
            b''.join([i.to_bytes(32, 'big') for i in self.previous_blocks]),
        ])
        
    def get_hash(self):
        return global_hash(self.to_bytes())
    
    def assert_internal_consistency(self):
        ''' self.assert_internal_consistency should validate the following:
        * version as expected
        * nonce not silly
        * timestamp not silly
        * target not silly
        * whatever_mr not silly
        * previous_blocks not silly
        
        'not silly' means the data 'looks' right (length, etc) but the information
        is not validated.
        '''
        pass
        
    def assert_validity(self, chain):
        ''' self.assert_validity does not validate merkle roots.
        Since the thing generating the merkle roots is stored in the block, a
        block is invlalid if its list of whatever does not produce the correct
        whatever_mr. The header is not invalid, however.
        
        self.assert_validity should validate the following:
        * self.timestamp no more than 15 minutes in the future and >= median of 
            last 100 blocks.
        * self.target is as expected based on past blocks
        * self.previous_blocks exist and are correct
        '''
        pass


class Block(Field):
    
    def fields():
        header = Header()
        uncles = List(Header())
        super_txs = List(SuperTx(), default=[])
        
    def init(self):
        self.parent_hash = 0
        
    def daisy_chain(other_block):
        ''' Inherit StateMaker, SuperState, etc from other_block.
        Remove other_block's access to StateMaker, etc.
        '''
        # TODO: This needs to be completed to test state on the blockchain.
        pass
        
    def get_hash(self):
        return self.header.get_hash()

    def add_super_txs(self, list_of_super_txs):
        self.state_maker.add_super_txs(list_of_super_txs)
        
    def assert_internal_consistency(self):
        ''' self.assert_internal_consistency should validate the following:
        * self.header internally consistent
        * self.uncles are all internally consistent
        * self.super_txs all internally consistent
        * self.header.transaction_mr equals merkle root of self.super_txs
        * self.header.uncles_mr equals merkle root of self.uncles
        '''
        pass
        
    def assert_validity(self, chain):
        ''' self.assert_validity should validate the following:
        * self.header.state_mr equals root of self.super_state
        '''
        pass
        
    
        
    
