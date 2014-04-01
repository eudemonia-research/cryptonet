import time, math

from utilities import *
from gpdht import *
from constants import *


def ghash(msg):
	''' This is the hash function that should be used EVERYWHERE in GPDHT.
	Currently defined to be SHA3.
	As always, should return a BANT '''
	return BANT(hashlib.sha3_256(bytes(msg)).digest())


eba = bytearray('')
def ADDBYTEARRAYS(a,b,carry=0):
	if (a == eba or b == eba) and carry == 0: return a + b
	if a == eba and b == eba and carry == 1: return bytearray([carry])
	for x,y in [(a,b),(b,a)]:
		if x == eba: return ADDBYTEARRAYS(y[:-1]+bytearray([0]), ADDBYTEARRAYS(bytearray([y[-1]]), bytearray([carry])))
	s = a[-1] + b[-1] + carry
	d = s % 256
	c = s/256
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
			self.this = bytearray(initString.decode('hex'))
		elif isinstance(initString, bytearray):
			self.this = initString[:]
		elif isinstance(initString, int):
			self.this = BANT(i2s(initString)).this
		elif isinstance(initString, BANT):
			self.this = initString.this[:]
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
		return BANT(ADDBYTEARRAYS(self.this, BANT(other).this))
	def __sub__(self, other):
		return BANT(i2h(int(self) - int(other)))
	def __mul__(self, other):
		return BANT(i2h(int(self) * int(other)))
	def __div__(self, other):
		return BANT(i2h(int(self) / int(other)))
	def __mod__(self, other):
		return BANT(i2h(int(self) % int(other)))
	def __pow__(self, other):
		return BANT(i2h(int(self) ** int(other)))
	def __xor__(self, other):
		return BANT(xor_strings(self.this.str(), other.this.str()))
		
	def __str__(self):
		return ''.join([chr(i) for i in self.this])
	def __repr__(self):
		return "BANT(\"" + self.hex() + "\", True)"
	def __int__(self):
		return sum( [self.this[::-1][i] * (2 ** (i * 8)) for i in range(len(self.this))] )
	def __float__(self):
		return float(self.__int__())
		
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
		return self.str().encode('hex')
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
	if isinstance(l, str):
		return BANT(l)
	elif isinstance(l, list):
		return [ALL_BANT(i) for i in l]
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
	if rlpIn == BANT(''): raise ValueError("RLP_DESERIALIZE: Requires nonempty BANT")
	
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
	rt = bytearray('')
	
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



#==============================================================================
# HashTree
#==============================================================================
		
		
class FakeHashNode:
	''' FakeHashNode should be used when the *hash* is known but the children are not. '''
	def __init__(self, h, ttl):
		self.myhash = h
		self.ttl = ttl
		self.parent = None
		
	def getHash(self):
		return self.myhash
		
	def setParent(self, parent):
		self.parent = parent
		return True
		
	def setChild(self, lr, newchild):
		raise TypeError("Type FakeHashNode can have no children")
		
	def getChild(self, lr):
		raise TypeError("Type FakeHashNode has no known children")
		
	def __len__(self):
		return len(self.getHash())
	
	
		
class HashNode:
	def __init__(self, children, ttl=None):
		self.myhash = None
		self.parent = None
		self.children = children
		self.ttl = children[0].ttl + 1
		self.children[0].setParent(self)
		if len(self.children) == 2: 
			self.children[1].setParent(self)
			assert children[0].ttl == children[1].ttl
		if ttl != None: self.ttl = ttl
		if len(children) < 1 or len(children) > 2: raise ValueError("HashNode: children must be a list/tuple of length 1 or 2")
		self.getHash()
		
	
	def __eq__(self, other):
		if len(self.children) == len(other.children) and self.ttl == other.ttl and self.children[0] == other.children[0]:
			if len(self.children) == 2 and self.children[1] == other.children[1]:
				return True
		return False
	
		
	def getHash(self, force=False):
		if self.myhash == None or force:
			# p0.hash ++ ttl ++ p1.hash
			tripconcat = lambda x: self.children[x[0]].getHash().concat(BANT(self.ttl-1).concat(self.children[x[1]].getHash()))
			if len(self.children) == 1: self.myhash = ghash(tripconcat([0,0]))
			else: self.myhash = ghash(tripconcat([0,1]))
			if self.parent != None: self.parent.getHash(True)
		return self.myhash
		
	def getChild(self, lr):
		return self.children[lr]
		
	def setChild(self, lr, newchild):
		if lr >= len(self.children):
			self.children.append(newchild)
		else:
			self.children[lr] = newchild
		self.children[lr].setParent(self)
		self.getHash(True)
		
	def setParent(self, parent):
		self.parent = parent
		return True
		
	def __len__(self):
		return len(self.getHash())
		
		
class HashTree:
	def __init__(self, init):		
		assert len(init) > 0
		self.n = len(init)
		
		chunks = init
		
		while len(chunks) > 1:
			newChunks = []
			for i in xrange(0,len(chunks),2):
				newChunks.append(HashNode(chunks[i:i+2]))
			chunks = newChunks
		self.root = chunks[0]
		self.height = self.root.ttl
		
		
	def doHash(self, msg):
		return ghash(msg)
		
		
	def rightmost(self, ttl):
		w = self.root 
		while True:
			if w.ttl == ttl: return w
			if w.ttl <= 0: raise ValueError("HashTree.rightmost: ttl provided is outside bounds")
			w = w.children[ len(w.children)-1 ]
		
		
	def leaves(self):
		w = self.root
		fringe = [w]
		while fringe[0].ttl != 0:
			newFringe = [j for i in fringe for j in i.children]
			fringe = newFringe
		return fringe
		
	def pathToPos(self, pos):
		length = int(math.ceil(math.log(self.n)/math.log(2)))
		return num2bits(pos, length)
		
	def pos(self, pos):
		n = self.n
		path = self.pathToPos(pos)
		node = self.root
		for d in path:
			node = node.children[d]
		return node
	
	def append(self, v=BANT(chr(0))):	
		if self.n == 1: 
			self.root = HashNode([self.root, v])
		else:
			n = self.n
			a = v
			ttl = 0
			while True:
				if n % 2 == 1:
					b = HashNode([self.rightmost(ttl), a])
					if b.ttl > self.root.ttl: self.root = b
					else: self.rightmost(ttl+2).setChild(1, b)
					break
				else:
					a = HashNode([a])
					n /= 2
					ttl += 1
		self.n += 1
		
		
	def update(self, pos, val):
		node = self.pos(pos).parent
		path = self.pathToPos(pos)
		node.setChild(path[-1], val)
		
			
	def getHash(self, force=False):
		return self.root.getHash(force)
		
	def __str__(self):
		return str(self.myhash)
	
	def __hash__(self):
		return int(self.getHash())
		
	def __eq__(self, other):
		if isinstance(other, str):
			return self.getHash().str() == other
		elif isinstance(other, BANT):
			return self.getHash() == other
		else:
			return self.getHash() == other.getHash()
		
		

#==============================================================================
# Forests, Chains, Etc
#==============================================================================
				
		
		
class Forest(object):
	''' Holds many trees '''
	def __init__(self):
		self.trees = set()
		
	def add(self, tree):
		assert isinstance(tree, HashTree)
		self.trees.add(tree)
		
	def remove(self, tree):
		self.trees.remove(tree)
	
		
class GPDHTChain(Forest):
	''' Holds a PoW chain and can answer queries '''
	# initial conditions must be updated when Chaindata structure updated
	_initialConditions = [
			BANT(1,padTo=4), # version
			BANT(0,padTo=4), # height
			BANT(b'\xff\xff\xff\x02'), # target
			BANT(0,padTo=6), # sigmadiff
			BANT(int(time.time()), padTo=6), # timestamp
			BANT(0, padTo=4), # votes
			BANT(bytearray(32)), # uncles
			BANT(bytearray(32)), # prevblock
		]
	_target1 = BANT(2**256-1)
	
	def __init__(self, genesisBlock=None, db=None):
		super(GPDHTChain, self).__init__()
		self.initComplete = False
		self.head = BANT(chr(0))
		self.db = db
		
		if genesisBlock != None: self.setGenesis(genesisBlock)
		else: self.setGenesis(self.mine(self.ChaindataTemplate()))
		
		
		
	def mine(self, Chaindata):
		# TODO : redo for new structure
		target = Chaindata.unpackedTarget
		message = BANT("It was a bright cold day in April, and the clocks were striking thirteen.")
		nonce = message.getHash()+1
		potentialTree = [i.getHash() for i in [Chaindata, Chaindata, message, message]]
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
		return (h, Chaindata)
		
	
	def ChaindataTemplate(self):
		# TODO : do a real block template here
		ret = self._initialConditions[:]
		# replace target with correct target
		# replace sigmadiff
		# set timestamp
		# set votes
		# set uncles
		# set prevblocks
		return Chaindata(ret)
	
	def hash(self, message):
		return ghash(message)
		
	def hashChaindata(self, cd):
		if isinstance(cd, Chaindata): return cd.getHash()
		return self.hash(RLP_SERIALIZE(cd))
		
	def setGenesis(self, block):
		tree, Chaindata = block
		print 'Setting Genesis Block'
		assert int(Chaindata.uncles) == 0
		assert int(Chaindata.prevblocks[0]) == 0
		assert len(Chaindata.prevblocks) == 1
		assert int(Chaindata.version) == 1
		
		target = Chaindata.unpackedTarget
		print "Chain.setGenesis: target : %064x" % target
		assert int(tree.getHash()) < target
		
		self.genesisTree = tree
		self.genesisHash = tree.getHash()
		self.genesisChaindata = Chaindata
		self.appid = Chaindata.getHash()
		
		self.headTree = self.genesisTree
		self.headChaindata = self.genesisChaindata
		
		self.addBlock(tree, Chaindata)
		
		
	# added sigmadiff stuff, need to test
	def addBlock(self, tree, Chaindata):
		if not validPoW(tree, Chaindata): return 'PoW failed'
		if self.db.exists(tree.getHash()): 
			print 'addBlock: %s already acquired' % tree.getHash().hex()
			return 'exists'
			
		print 'addBlock: Potential block', tree.getHash().hex()
		print 'addBlock: block.leaves:', tree.leaves()
		
		if self.initComplete == False:
			assert Chaindata.prevblocks[0] == BANT(0, padTo=32)
			assert len(Chaindata.prevblocks) == 1
			maxsigmadiff = BANT(0)
		else:
			print 'addBlock: repr(prevblock):', repr(Chaindata.prevblocks[0])
			if Chaindata.prevblocks[0] not in self.trees:
				raise ValueError('Prevblock[0] does not exist')
			maxsigmadiff = self.headChaindata.sigmadiff
			
		sigmadiff = self.calcSigmadiff(Chaindata)
		if maxsigmadiff < sigmadiff:
			debug('New head of chain : %s' % tree.getHash())
			self.head = tree
			self.headChaindata = Chaindata
			
		# TODO : these should not be asserts
		assert block.pos(0) == self.appid
		assert block.pos(1) == Chaindata.getHash()
		
		print 'addBlock: NEW BLOCK', tree.getHash().hex()
		self.add(tree)
		
		if self.initComplete == False:
			self.initComplete = True
		
		self.db.dumpTree(tree)
		self.db.dumpChaindata(Chaindata)
		self.db.setAncestors(tree, Chaindata.prevblocks[0])
		
		return True
		
		
	# need to test
	def calcSigmadiff(self, cd):
		''' given Chaindata, calculate the sigmadiff '''
		# TODO : test
		prevblockhash = cd.prevblocks[0]
		if prevblockhash == 0:
			prevsigmadiff = BANT(0)
		else:
			prevblocklist = self.db.getEntry(prevblockhash)
			prevChaindata = Chaindata(self.db.getEntry(prevblocklist[1])) # each GPDHT block has 2nd entry as Chaindata hash
			prevsigmadiff = prevChaindata.sigmadiff
		target = cd.unpackedTarget
		diff = self._target1 / target
		sigmadiff = prevsigmadiff + diff
		return sigmadiff
	
	
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
		
		
	def getTopBlock(self):
		return self.head
		
		
	def loadChain(self):
		# TODO : load chainstate from database
		pass
		#self.db.getSuccessors(self.genesisHash)
		
	
	def learnOfDB(self, db):
		self.db = db
		self.loadChain()
		
		

#==============================================================================
# Network Specific - Value Laden Data Structures
#==============================================================================
		

class Chaindata:
	def __init__(self, cd):
		# ["version", "height", "target", "sigmadiff", "timestamp", "votes", "uncles"] # prev1, 2, 4, 8, ... appended here
		self.version = cd[CDM['version']]
		self.height = cd[CDM['height']]
		self.target = cd[CDM['target']]
		self.sigmadiff = cd[CDM['sigmadiff']]
		self.timestamp = cd[CDM['timestamp']]
		self.votes = cd[CDM['votes']]
		self.uncles = cd[CDM['uncles']]
		# there is an ancestry summary here
		self.prevblocks = cd[CDM['prevblock']:]
		
		self.unpackedTarget = unpackTarget(self.target)
		
		self.hash = ghash(RLP_SERIALIZE(cd))
		
	def getHash(self):
		return self.hash
		
class Uncles:
	def __init__(self, ul):
		self._uncles = []
		for uncle in ul:
			# TODO : validate Chaindata in hashtree
			self._uncles.append( HashTree(uncle[UM['hashtree']]) )
		self._tree = HashTree(self._uncles)
			
	''' unsure if this is needed...
	def __getitem__(self, key):
		return self._uncles.__getitem__(key)
		
	def __setitem__(self, key, value):
		return self._uncles.__setitem__(key, value)
	'''
	
	def getHash():
		return self._tree.getHash()		
	
		

	
#==============================================================================
# Constants
#==============================================================================
		

z32 = BANT('',padTo=32)
