import time, math

from hashlib import sha256
from utilities import *

from bitcoin.base58 import encode as b58encode, decode as b58decode


def hashfunc(msg):
	return BANT(sha256(str(msg)).digest())

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
		return hashfunc(self)
	
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
	#return BANT(b58decode(b58s))
def ENCODEBANT(b):
	return b.hex()
	#return b58encode(b.str())
	
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
	
	return BANT(ret)
			


#==============================================================================
# JSON OPERATIONS
#==============================================================================	
	
	
def json_str_to_bant(obj):
	print 'json_str_to_bant - %s' % str(obj)
	if isinstance(obj, str):
		return BANT(obj.decode('hex'))
	if isinstance(obj, unicode):
		return BANT(str(obj).decode('hex'))
	if isinstance(obj, list):
		rt = []
		for a in obj: rt.append(json_str_to_bant(a))
		return rt
	if isinstance(obj, dict):
		rt = {}
		for k,v in obj.iteritems():
			rt[k] = json_str_to_bant(v)
		return rt
	return obj
	
def json_loads(obj):
	print 'json_loads:',obj
	a = json.loads(obj)
	print 'json_loads:', a
	return json_str_to_bant(a)
	



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
			if len(self.children) == 1: self.myhash = hashfunc(tripconcat([0,0]))
			else: self.myhash = hashfunc(tripconcat([0,1]))
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
		return hashfunc(msg)
		
		
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
	headerMap = dict([(title,n) for n,title in enumerate(["version", "height", "prevblock", "uncles", "target", "timestamp", "votes"])])
	_blockInfoTemplate = [
			BANT(1,padTo=4), # version
			BANT(0,padTo=4), # height
			BANT(bytearray(32)), # prevblock
			BANT(bytearray(32)), # uncles
			BANT(b'\x0f\xff\xff\x01'), # target
			BANT(int(time.time()), padTo=6), # timestamp
			BANT(0, padTo=4), # votes
		]
	_target1 = BANT(2**256-1)
	
	def __init__(self, genesisheader=None, db=None):
		super(GPDHTChain, self).__init__()
		self.initComplete = False
		self.head = BANT(chr(0))
		self.db = db
		
		self.decs = {}
		self.hashfunc = hashfunc
		if genesisheader != None: self.setGenesis(genesisheader)
		else: self.setGenesis(self.mine(self.blockInfoTemplate()))
		
		
		
	def mine(self, blockInfoTemplate):
		blockInfoHash = self.hashBlockInfo(blockInfoTemplate)
		blockInfoRLP = RLP_SERIALIZE(blockInfoTemplate)
		target = unpackTarget(blockInfoTemplate[self.headerMap['target']])
		message = BANT("It was a bright cold day in April, and the clocks were striking thirteen.")
		nonce = message.getHash()
		potentialTree = [i.getHash() for i in [blockInfoRLP, blockInfoRLP, message, nonce]]
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
				print count, PoW.hex()
		print 'Chain.mine: Found Soln : %s', PoW.hex()
		return (h, blockInfoTemplate)
		
	
	def blockInfoTemplate(self):
		return self._blockInfoTemplate
			
	
	
	def hash(self, message):
		return hashfunc(message)
		
	def hashBlockInfo(self, blockInfo):
		return self.hash(RLP_SERIALIZE(blockInfo))
		
		
	def setGenesis(self, bPair):
		tree, blockInfo = bPair
		print 'Setting Genesis Block'
		assert int(blockInfo[self.headerMap["uncles"]]) == 0
		assert int(blockInfo[self.headerMap["prevblock"]]) == 0
		assert int(blockInfo[self.headerMap["version"]]) == 1
		
		self.target = unpackTarget(blockInfo[self.headerMap["target"]])
		print "Chain.setGenesis: target : %064x" % self.target
		assert int(tree.getHash()) < self.target
		
		self.genesisInfo = blockInfo
		self.genesisTree = tree
		self.genesisHash = tree.getHash()
		self.appid = RLP_SERIALIZE(blockInfo).getHash()
		
		self.head = self.genesisTree.getHash()
		self.headInfo = self.genesisInfo
		
		self.addBlock(tree, blockInfo)
		
		
	# added cumulative difficulty stuff, need to test
	def addBlock(self, block, blockInfo):
		if self.db.exists(block.getHash()): 
			print 'addBlock: %s already acquired' % block.getHash().hex()
			return 'Exists'
		print 'addBlock: Potential block', block.getHash().hex()
		print 'addBlock: block.leaves:', block.leaves()
		if self.initComplete == False:
			assert blockInfo[self.headerMap['prevblock']] == BANT(bytearray(32))
			hcdiff = BANT(0)
		else:
			print 'addBlock: repr(prevblock):', repr(blockInfo[self.headerMap['prevblock']])
			assert blockInfo[self.headerMap['prevblock']] in self.trees
			hcdiff = self.cumulativeDifficulty(self.headInfo)
		cdiff = self.cumulativeDifficulty(blockInfo)
		if hcdiff < cdiff:
			self.head = block.getHash()
			self.headInfo = blockInfo
		h = self.hashBlockInfo(blockInfo)
		print block.leaves()
		print repr(block.pos(0))
		print repr(self.genesisHash)
		assert self.appid == block.pos(0)
		assert h == block.pos(1)
		
		print 'addBlock: NEW BLOCK', block.getHash().hex()
		self.add(block)
		
		if self.initComplete == False:
			self.initComplete = True
		
		self.db.dumpTree(block)
		self.db.dumpList(blockInfo)
		self.db.setAncestors(block, blockInfo[self.headerMap['prevblock']])
		self.db.setEntry(block.getHash() + blockInfo[self.headerMap['target']], [cdiff]) # note, because of this target cannot equal 0 or be a power of 2.
		
		return True
		
	def headInfo(self):
		print self.db.getEntry(self.head)
		return self.db.getEntry(self.db.getEntry(self.head)[1])
		
	# need to test
	def cumulativeDifficulty(self, blockInfo):
		prevblock = blockInfo[self.headerMap['prevblock']]
		if prevblock == 0:
			return BANT(0)
		prevBlockList = self.db.getEntry(prevblock)
		prevBlockInfo = self.db.getEntry(prevBlockList[1])
		prevCumulativeDifficulty = self.db.getEntry(prevBlockInfo[self.headerMap['target']] + prevblock)[0]
		target = blockInfo[self.headerMap['target']]
		diff = self._target1 / unpackTarget(target)
		cdiff = prevCumulativeDifficulty + diff
		print repr(cdiff)
		return cdiff
	
	
	def validAlert(self, alert):
		# TODO : return True if valid alert
		pass
		
	
	def getSuccessors(self, blocks, stop):
		# TODO : find HCB and then some successors until stop or max num
		return [self.db.getSuccessors(b) for b in blocks]
		
		
	def getTopBlock(self):
		return self.head
		
		
	def loadChain(self):
		self.db.getSuccessors(self.genesisHash)
		
	
	def learnOfDB(self, db):
		self.db = db
		self.loadChain()
		
		
		

#==============================================================================
# Node
#==============================================================================
		
		
class Node:
	''' Simple class to hold node info '''
	def __init__(self, ip, port):
		self.ip = ip
		self.port = port
		self.versionInfo = None
		self.alive = False
		self.score = 0
		self.testAlive()
		
		self.about = None
		
	def sendMessage(self, path, msgdict, method="POST"):
		fireHTTP(self, path, msgdict, method)
		
	def testAlive(self):
		# TODO : request /about from node, true if recieved
		self.alive = True
		



#==============================================================================
# Network Specific - Value Laden Data Structures
#==============================================================================
		

class Block:
	def __init__(hashtree):
		pass
		

	
#==============================================================================
# Constants
#==============================================================================
		

z32 = BANT('',padTo=32)
