from cryptonet.gpdht import *
from cryptonet.debug import *
from encodium import *
import math

#==============================================================================
# HashTree
#==============================================================================

class MerkleLeavesToRoot(Field):
    def fields():
        leaves = List(Integer(width=32))
        
    def init(self):
        self.update()
        
    def update(self):
        t = self.leaves[:]
        while len(t) > 1: 
            if len(t) % 2 != 0: t.append(int.from_bytes(b'\x00'*32, 'big'))
            t = [ghash(t[i].to_bytes(32,'big') + t[i+1].to_bytes(32,'big')) for i in range(0,len(t),2)]
        self.root = t[0]
        
    def getHash(self):
        return self.root
        
MerkleTree = MerkleLeavesToRoot

#============================
# ChainVars
#============================

class ChainVars:
    def __init__(self, **kwargs):
        pass
            

#============================
# Primatives
#============================
        
class BaseField(Field):
    def getHash(self):
        return ghash(self.serialize())

class ListFieldPrimative(BaseField):
    def init(self):
        def __len__(self):
            return len(self.contents)
        self.__len__ = __len__
    
    def extend(self, item):
        self.contents.append(item)
    
    def append(self, item):
        self.contents.append(item)
        
    def __getitem__(self, index):
        return self.contents[index]
        
    def __setitem__(self, index, value):
        self.contents[index] = value
        
    def len(self):
        return len(self.contents)  
        
    def __iter__(self):
        return self.contents

        
class IntList(ListFieldPrimative):
    def fields():
        contents = List(Integer(), default=[])

class HashList(IntList):
    def fields():
        contents = List(Integer(length=32), default=[])

class BytesList(ListFieldPrimative):
    def fields():
        contents = List(Bytes(), default=[])
        


#============================
# Messages
#============================


class Intro(BaseField):
    def fields():
        version = Integer(default=1, width=4)
        services = Integer(default=1, width=4)
        timestamp = Integer(default=1, width=5)
        user_agent = String(default='cryptonet/0.0.1/', max_length=32)
        topblock = Integer(length=32)
        relay = Integer(default=0, length=1)
        leaflets = List(Bytes(length=32), default=[])
        

RequestBlocksMessage = HashList
BlocksMessage = BytesList
        
        
        
        
#============================
# Blocks, headers, transactions
#============================

class BitcoinTransactionOutPoint(BaseField):
    ''' not an output from a tx '''
    def fields():
        txhash = Integer(length=32)
        index = Integer(length=4)

class BitcoinTransactionInput(BaseField):
    def fields():
        previous_output = BitcoinTransactionOutPoint()
        sigscript = BytesList()
        sequence = Integer(length=4)
    
class BitcoinTransactionOutput(BaseField):
    def fields():
        value = Integer(length=8)
        txout = Bytes()

class BitcoinTransaction(BaseField):
    def fields():
        version = Integer(length=4)
        inputs = List(BitcoinTransactionInput(), default=[])
        outputs = List(BitcoinTransactionOutput(), default=[])
        locktime = Integer(length=4)
        
        
class BitcoinTransactionMerkleTree(BaseField):
    def fields():
        transactions = List(BitcoinTransaction(), default=[])
        merkleroot = Integer(length=32, optional=True, default=0)
        
    def init(self):
        tempMT = MerkleLeavesToRoot.make(leaves=self.transactions)
        self.merkleroot = tempMT.getHash()
    
    def getHash(self):
        return self.merkleroot

class BitcoinHeader(BaseField):
    def fields():
        version = Integer(length=4)
        prevblock = Integer(length=32)
        merkleroot = Integer(length=32)
        timestamp = Integer(length=4)
        nbits = Bytes(length=4)
        nonce = Integer(lenght=4)
        
    def getHash(self):
        return ghash(b''.join([
            self.version.to_bytes(4,'big'),
            self.prevblock.to_bytes(32, 'big'),
            self.merkleroot.to_bytes(32, 'big'),
            self.timestamp.to_bytes(4, 'big'),
            self.nbits,
            self.nonce.to_bytes(4, 'big')
            ])

class BitcoinBlock(Field):
    def fields():
        header = Header()
        transactions = BitcoinTransactionMerkleTree()
        
    def getHash(self):
        return self.header.getHash()
