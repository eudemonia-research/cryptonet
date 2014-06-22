from cryptonet.utilities import global_hash
from cryptonet.debug import debug
from cryptonet.constants import SOFTWARE_VERSION
from encodium import *
import math

#==============================================================================
# HashTree
#==============================================================================

class MerkleLeavesToRoot(Field):
    def fields():
        leaves = List(Integer(length=32))

    def init(self):
        self.update()

    def check_leaves(self):
        debug('checking leaves')
        assert len(self.leaves) > 0

    def update(self):
        if len(self.leaves) == 0:
            self.root = 0
        try:
            t = self.leaves[:]
            while len(t) > 1:
                if len(t) % 2 != 0: t.append(int.from_bytes(b'\x00' * 32, 'big'))
                t = [self.my_hash(t[i].to_bytes(32, 'big') + t[i + 1].to_bytes(32, 'big')) for i in range(0, len(t), 2)]
            self.root = t[0]
        except:
            debug('MerkleTree update, leaves :', self.leaves)

    def get_hash(self):
        return self.root

    def my_hash(self, msg):
        return global_hash(msg)


class MerkleBranchToRoot(Field):

    def fields():
        hash = Integer(length=32)
        hash_branch = List(Integer(length=32))
        lr_branch = List(Integer(length=1))

    def init(self):
        assert len(self.hash_branch) == len(self.lr_branch)
        self.update()

    def update(self):
        rolled_up = self.hash
        for i in range(len(self.hash_branch)):
            if self.lr_branch[i] == 0:
                rolled_up = self.my_hash(self.hash_branch[i].to_bytes(32, 'big') + rolled_up.to_bytes(32, 'big'))
            else:
                rolled_up = self.my_hash(rolled_up.to_bytes(32, 'big') + self.hash_branch[i].to_bytes(32, 'big'))
        self.root = rolled_up

    def get_hash(self):
        return self.root

    def my_hash(self, msg):
        return global_hash(msg)





MerkleTree = MerkleLeavesToRoot

#============================
# ChainVars
#============================

class ChainVars:
    def __init__(self, **kwargs):
        self.seeds = [('127.0.0.1', 32764)]
        self.address = (b'127.0.0.1', 12345)
        self.genesis_binary = None
        self.mine = False
        # TODO : decide what default should be - devs pubkey or 0 pubkey (which means a network will be forced
        # to change it otherwise it'll get DOSed.
        self.alert_pubkey_x = 55066263022277343669578718895168534326250603453777594175500187360389116729240


#============================
# Primitives
#============================


class BaseField(Field):
    ''' DOES NOT WORK - ENCODIUM DOESN'T SUPPORT INHERITANCE YET
    '''
    def __init__(self, *args, **kwargs):
        Field.__init__(self, *args, **kwargs)
        self.default_options = Field.default_options

    def get_hash(self):
        return global_hash(self.serialize())


class ListFieldPrimative(Field):
    ''' DOES NOT WORK - ENCODIUM DOESN'T SUPPORT INHERITANCE YET
    '''
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
        return None


class IntList(ListFieldPrimative):
    ''' DOES NOT WORK - ENCODIUM DOESN'T SUPPORT INHERITANCE YET
    '''
    def fields():
        contents = List(Integer(), default=[])

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

    def __len__(self):
        return len(self.contents)

    def __iter__(self):
        return self.contents.__iter__()

    def __eq__(self, other):
        return self.contents == other

    def get_hash(self):
        return global_hash(self.serialize())


class HashList(IntList):
    def fields():
        contents = List(Integer(length=32), default=[])

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
        return self.contents.__iter__()

    def get_hash(self):
        return global_hash(self.serialize())


class BytesList(ListFieldPrimative):
    def fields():
        contents = List(Bytes(), default=[])

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
        return self.contents.__iter__()

    def get_hash(self):
        return global_hash(self.serialize())


#===============================================================================
# Messages
#===============================================================================


class Intro(Field):
    def fields():
        version = Integer(default=1, width=4)
        services = Integer(default=1, width=4)
        timestamp = Integer(default=1, width=5)
        user_agent = String(default='cryptonet/0.0.1/', max_length=32)
        top_block = Integer(length=32)
        relay = Integer(default=0, length=1)
        hash_list = List(Bytes(length=32), default=[])

    def get_hash(self):
        return global_hash(self.serialize())


RequestBlocksMessage = HashList
BlocksMessage = BytesList

"""

#===============================================================================
# Stand-alone Blocks, headers, transactions
#===============================================================================


class StandaloneBlock(Field):
    def fields():
        header = StandaloneHeader()
        transactions = StandardTransactionMerkleTree()
        states = StandardStateMerkleTree()
        
        
#===============================================================================
# Standard Blocks, headers, transactions
#===============================================================================

# Default to balance based transactions, not input/output txs like Bitcoin

class StandardSignature(Field):
    def fields():
        v = Integer(length=1)
        r = Integer(length=32)
        s = Integer(length=32)

# subtx: [data[0], data[1], ..., data[n]]
class StandardSubtransaction(Field):
    def fields():
        data = List() # unsure if these should be restricted to numbers or bytes or w/e just yet

class StandardTransaction(Field):
    def fields():
        nonce = Integer(length=32)
        subtxlist = List(StandardSubtransaction())
        signature = StandardSignature()
        
StandardTransactionMerkleTree = MerkleTree
StandardStateMerkleTree = MerkleTree
StandardState = MerklePatriciaDict
        
class StandardHeader(Field):
    # since standard blocks will run on the grachten many traditional elements
    # of headers, like target, timestamp, etc, are outsourced to the grachten
    # blockchain. There should be some API so blocks/headers can access this
    # though. Perhaps access to the entire grachten block? Maybe just provide
    # with authenticated list and trust that? Unsure as yet.
    #
    # Period: How often blocks appear
    def fields():
        version = Integer(length=2)
        period = Integer(length=2) # max block time once every ~18 hours for 2 byte int
        transactionsMR = Integer(length=32)
        statesMR = Integer(length=32)
        previous_block = Integer(length=32)

class StandardBlock(Field):
    def fields():
        header = StandardHeader()
        transactions = StandardTransactionMerkleTree()
        states = StandardStateMerkleTree()

#===============================================================================
# Bitcoin Blocks, headers, transactions
# Not yet complete, need to validate
#===============================================================================

class BitcoinTransactionOutPoint(Field):
    ''' not an output from a tx '''
    def fields():
        txhash = Integer(length=32)
        index = Integer(length=4)

class BitcoinTransactionInput(Field):
    def fields():
        previous_output = BitcoinTransactionOutPoint()
        sigscript = BytesList()
        sequence = Integer(length=4)
    
class BitcoinTransactionOutput(Field):
    def fields():
        value = Integer(length=8)
        txout = Bytes()

class BitcoinTransaction(Field):
    def fields():
        version = Integer(length=4)
        inputs = List(BitcoinTransactionInput(), default=[])
        outputs = List(BitcoinTransactionOutput(), default=[])
        locktime = Integer(length=4)
        
        
class BitcoinTransactionMerkleTree(Field):
    def fields():
        transactions = List(BitcoinTransaction(), default=[])
        merkleroot = Integer(length=32, optional=True, default=0)
        
    def init(self):
        tempMT = MerkleLeavesToRoot.make(leaves=self.transactions)
        self.merkleroot = tempMT.get_hash()
    
    def get_hash(self):
        return self.merkleroot

class BitcoinHeader(Field):
    def fields():
        version = Integer(length=4)
        previous_block = Integer(length=32)
        merkleroot = Integer(length=32)
        timestamp = Integer(length=4)
        nbits = Bytes(length=4)
        nonce = Integer(lenght=4)
        
    def get_hash(self):
        return global_hash(b''.join([
            self.version.to_bytes(4,'big'),
            self.previous_block.to_bytes(32, 'big'),
            self.merkleroot.to_bytes(32, 'big'),
            self.timestamp.to_bytes(4, 'big'),
            self.nbits,
            self.nonce.to_bytes(4, 'big')
            ]))
            
class BitcoinBlock(Field):
    def fields():
        header = Header()
        transactions = BitcoinTransactionMerkleTree()
        
    def get_hash(self):
        return self.header.get_hash()

"""
