'''gpdht.py contains functions to validate the protocol'''

import hashlib, sys
import sha3
from binascii import hexlify, unhexlify

#from utilities import *


#==============================================================================
# GENERAL CRYPTONET FUNCTIONS
#==============================================================================
    
    

def validPoW(ht, cd):
    return ht.getHash() < cd.unpackedTarget

def ghash(msg):
    ''' This is the hash function that should be used EVERYWHERE in GPDHT.
    Currently defined to be SHA3.
    As always, should return a BANT '''
    s = hashlib.sha3_256()
    s.update(bytes(msg))
    return BANT(s.digest())



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
    '''
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
        '''
    
    def __init__(self, chainVars, genesisBlock=None, db=None):
        self.initialized = False
        self.head = None
        self.db = db
        self.miner = None
        self.blocks = set()
        self.blockhashes = set()
        
        self.genesisBlock = None
        if genesisBlock != None: self.setGenesis(genesisBlock)
        
        
    '''def mine(self, chaindata):
        # TODO : redo for new structure
        target = chaindata.unpackedTarget
        message = BANT("It was a bright cold day in April, and the clocks were striking thirteen.")
        nonce = message.getHash()+1
        potentialTree = [i.getHash() for i in [chaindata, chaindata, message, message]]
        h = HashTree(potentialTree)
        count = 0
        while True:
            count += 1
            h.update(3, nonce)
            PoW = h.getHash()
            if PoW < target:
                break
            nonce += 1
            if count % 10000 == 0:
                debug("Mining Genesis : %d : %s" % (count, PoW.hex()))
        debug('Chain.mine: Found Soln : %s' % PoW.hex())
        return (h, chaindata)'''
        
    def restartMiner(self):
        if self.miner != None:
            self.miner.restart()
        
    def setMiner(self, miner):
        self.miner = miner
    
    def hash(self, message):
        return ghash(message)
        
        '''
    def hashChaindata(self, cd):
        if isinstance(cd, Chaindata): return cd.getHash()
        return self.hash(RLP_SERIALIZE(cd))
        '''
        
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
        
        self.db.setEntry(block.getHash(), block)
        self.db.setAncestors(block)
        self.blocks.add(block)
        self.blockhashes.add(block.getHash())
        
        
        if self.initialized == False:
            self.initialized = True
        
        print('added block %d, hash: %x' % (block.height, block.getHash()))
        
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

#==============================================================================
# BANT STUFF
#==============================================================================
    
    
eba = bytearray(b'')
def ADDBYTEARRAYS(a,b,carry=0):
    if (a == eba or b == eba) and carry == 0: return a + b
    if a == eba and b == eba and carry == 1: return bytearray([carry])
    for x,y in [(a,b),(b,a)]:
        if x == eba: 
            return ADDBYTEARRAYS(y[:-1]+bytearray([0]), ADDBYTEARRAYS(bytearray([y[-1]]), bytearray([carry])))
    s = a[-1] + b[-1] + carry
    d = s % 256
    c = s//256
    return ADDBYTEARRAYS(a[:-1],b[:-1],c) + bytearray([d])


class BANT:
    '''Byte Array Number Thing
    Special data structure where it acts as a number and a byte array/list
    Slices like a byte array
    Adds and compares like a number
    Hashes like a byte array
    '''
    def __init__(self, initString=b'\x00', fromHex=False, padTo=0):
        if fromHex == True:
            '''input should be a string in hex encoding'''
            self.this = bytearray(unhexlify(initString))
        elif isinstance(initString, bytearray):
            self.this = initString[:]
        elif isinstance(initString, bytes):
            self.this = bytearray(initString)
        elif isinstance(initString, int):
            self.this = bytearray(initString.to_bytes((initString.bit_length() // 8) + 1, 'big'))
        elif isinstance(initString, BANT):
            self.this = initString.this[:]
        elif isinstance(initString, str):
            self.this = bytearray(bytes(initString.encode()))
        else:
            self.this = bytearray(bytes(initString))
            
        while padTo - len(self.this) > 0: self.this = bytearray([0]) + self.this
            
        self.isBANT = True
        self.ttl = 0
        self.parent = None
        
        
    def __lt__(self, other):
        return int(self) < int(other)
    def __gt__(self, other):
        return int(self) > int(other)
    def __eq__(self, other):
        if other == None: return False
        if isinstance(other, str):
            return self.this == other
        return int(self) == int(other)
    def __ne__(self, other):
        return not (self == other)
    def __le__(self, other):
        return int(self) <= int(other)
    def __ge__(self, other):
        return int(self) >= int(other)
    def __cmp__(self, other):
        return BANT(int(self) - int(other))
        
    def __len__(self):
        return len(self.this)
    def __getitem__(self,key):
        return BANT(self.this[key])
    def __setitem__(self,key,value):
        self.this[key] = value
        
    # do I need to do the r___ corresponding functions? (__radd__ for example)
    def __add__(self, other):
        # TODO : should adding a STRING to a BANT append or addition?
        if isinstance(other, str): return BANT(self.this + bytearray(other))
        if isinstance(other, bytearray): return BANT(self.this + bytearray(other))
        return BANT(ADDBYTEARRAYS(self.this, BANT(other).this))
    def __sub__(self, other):
        return BANT(int(self) - int(other))
    def __mul__(self, other):
        return BANT(int(self) * int(other))
    def __truediv__(self, other):
        return BANT(int(self) / int(other))
    def __floordiv__(self, other):
        return BANT(int(self) // int(other))
    def __mod__(self, other):
        return BANT(int(self) % int(other))
    def __pow__(self, other):
        return BANT(int(self) ** int(other))
    def __xor__(self, other):
        return BANT(xor_strings(self.this.str(), other.this.str()))
        
    def __str__(self):
        return ''.join([chr(i) for i in self.this])
    def __repr__(self):
        return str(b"BANT(\"" + self.hex() + b"\", True)")
    def __int__(self):
        return sum( [self.this[::-1][i] * (2 ** (i * 8)) for i in range(len(self.this))] )
    def __float__(self):
        return float(self.__int__())
    def __bytes__(self):
        return bytes(self.this)
        
    def __hash__(self):
        return int(self)
    
    def getHash(self):
        return ghash(self)
    
    def encode(self, f='bant'):
        if f == 'bant': return ENCODEBANT(self)
        elif f == 'hex': return self.hex()
    def to_json(self):
        return self.encode()
    
    def hex(self):
        return hexlify(bytes(self.this))
    def concat(self, other):
        return BANT(self.this + other.this)
    def raw(self):
        return self.this
    def str(self):
        return self.__str__()
    def int(self):
        return self.__int__()
        
    def setParent(self, parent):
        self.parent = parent
        

def DECODEBANT(s):
    return BANT(s.decode('hex'))
def ENCODEBANT(b):
    return b.hex()
    
def ALL_BANT(l):
    if isinstance(l, str) or isinstance(l, int) or isinstance(l, bytes):
        return BANT(l)
    elif isinstance(l, list):
        return [ALL_BANT(i) for i in l]
    else:
        return l
        
        
def ALL_BYTES(l):
    if isinstance(l, str) or isinstance(l, int) or isinstance(l, bytes) or isinstance(l, BANT):
        return bytes(l)
    elif isinstance(l, list):
        return [ALL_BYTES(i) for i in l]
    else:
        return l
        
        


#==============================================================================
# RLP OPERATIONS
#==============================================================================
    
def RLP_WRAP_DESERIALIZE(rlpIn):
    if rlpIn.raw()[0] >= 0xc0:
        if rlpIn.raw()[0] > 0xf7:
            sublenlen = rlpIn.raw()[0] - 0xf7
            sublen = rlpIn[1:sublenlen+1].int()
            msg = rlpIn[sublenlen+1:sublenlen+sublen+1]
            rem = rlpIn[sublenlen+sublen+1:]
        
        else:
            sublen = rlpIn.raw()[0] - 0xc0
            msg = rlpIn[1:sublen+1]
            rem = rlpIn[sublen+1:]
            
        o = []
        while len(msg) > 0:
            t, msg = RLP_WRAP_DESERIALIZE(msg)
            o.append(t)
        return o, rem
    
    elif rlpIn.raw()[0] > 0xb7:
        subsublen = rlpIn.raw()[0] - 0xb7
        sublen = rlpIn[1:subsublen+1].int()
        msg = rlpIn[subsublen+1:subsublen+sublen+1]
        rem = rlpIn[subsublen+sublen+1:]
        return msg, rem
        
    elif rlpIn.raw()[0] >= 0x80:
        sublen = rlpIn.raw()[0] - 0x80
        msg = rlpIn[1:sublen+1]
        rem = rlpIn[sublen+1:]
        return msg, rem
    
    else:
        return rlpIn[0], rlpIn[1:]
        
def RLP_DESERIALIZE(rlpIn):
    if not isinstance(rlpIn, BANT): raise ValueError("RLP_DESERIALIZE requires a BANT as input")
    if len(rlpIn) == 0: return rlpIn
    ret, rem = RLP_WRAP_DESERIALIZE(rlpIn)
    if rem != BANT(''): raise ValueError("RLP_DESERIALIZE: Fail, remainder present")
    return ret
    
def RLP_ENCODE_LEN(b, islist = False):
        if len(b) == 1 and not islist and b < 0x80:
            return bytearray([])
        elif len(b) < 56:
            if not islist: return bytearray([0x80+len(b)])
            return bytearray([0xc0+len(b)]) 
        else:
            if not islist: return bytearray([0xb7+len(i2s(len(b)))]) + bytearray(i2s(len(b)))
            return bytearray([0xf7+len(i2s(len(b)))]) + bytearray(i2s(len(b)))
    
def RLP_SERIALIZE(blistIn):
    rt = bytearray(b'')
    
    if isinstance(blistIn, BANT):
        rt.extend(RLP_ENCODE_LEN(blistIn) + blistIn.raw())
        ret = rt
    elif isinstance(blistIn, list):
        for b in blistIn:
            rt.extend( RLP_SERIALIZE(b).raw() )
        
        ret = RLP_ENCODE_LEN(rt, True)
        ret.extend(rt)
    else:
        raise ValueError('input is not a BANT or a list')
    
    return BANT(ret)
