import time, math

from utilities import *
from gpdht import *
from constants import *



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
		if other == None: return False
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
			for i in range(0,len(chunks),2):
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
					n //= 2
					ttl += 1
		self.n += 1
		
		
	def update(self, pos, val):
		node = self.pos(pos).parent
		path = self.pathToPos(pos)
		node.setChild(path[-1], val)
		
			
	def getHash(self, force=False):
		return self.root.getHash(force)
		
	def __str__(self):
		return str(self.getHash().hex())
	
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
		else: self.setGenesis(self.mine(self.chaindataTemplate()))
		
		
		
	def mine(self, chaindata):
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
		return (h, chaindata)
		
	
	def chaindataTemplate(self):
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
		tree, chaindata = block
		debug('Setting Genesis Block')
		assert int(chaindata.uncles) == 0
		assert int(chaindata.prevblocks[0]) == 0
		assert len(chaindata.prevblocks) == 1
		assert int(chaindata.version) == 1
		
		target = chaindata.unpackedTarget
		debug("Chain.setGenesis: target : %064x" % target)
		assert int(tree.getHash()) < target
		
		self.genesisTree = tree
		self.genesisHash = tree.getHash()
		self.genesisChaindata = chaindata
		self.appid = chaindata.getHash()
		
		self.headTree = self.genesisTree
		self.headChaindata = self.genesisChaindata
		
		debug('Adding Genesis; details:')
		debug('\ttree: %s' % tree.leaves())
		debug('\tchaindata: %s' % chaindata.rawlist)
		self.addBlock(tree, chaindata)
		
		
	# added sigmadiff stuff, need to test
	def addBlock(self, tree, chaindata):
		if not validPoW(tree, chaindata): return 'PoW failed'
		if self.db.exists(tree.getHash()): 
			debug('addBlock: %s already acquired' % tree.getHash().hex())
			return 'exists'
			
		debug('addBlock: Potential block : %s' % repr(tree.getHash().hex()))
		debug('addBlock: block.leaves : %s' % repr(tree.leaves()))
		
		if self.initComplete == False:
			assert chaindata.prevblocks[0] == BANT(0, padTo=32)
			assert len(chaindata.prevblocks) == 1
			maxsigmadiff = BANT(0)
		else:
			debug('addBlock: repr(prevblock):', repr(chaindata.prevblocks[0]))
			if chaindata.prevblocks[0] not in self.trees:
				raise ValueError('Prevblock[0] does not exist')
			maxsigmadiff = self.headChaindata.sigmadiff
			
		sigmadiff = self.calcSigmadiff(chaindata)
		if maxsigmadiff < sigmadiff:
			debug('New head of chain : %s' % tree.getHash().hex())
			self.head = tree
			self.headChaindata = chaindata
			
		# TODO : these should not be asserts
		assert tree.pos(0) == self.appid
		assert tree.pos(1) == chaindata.getHash()
		
		debug( 'addBlock: NEW BLOCK : %s' % repr(tree.getHash().hex()) )
		self.add(tree)
		
		if self.initComplete == False:
			self.initComplete = True
		
		self.db.dumpTree(tree)
		self.db.dumpChaindata(chaindata)
		self.db.setAncestors(tree, chaindata.prevblocks[0])
		
		return True
		
		
	# need to test
	def calcSigmadiff(self, cd):
		''' given chaindata, calculate the sigmadiff '''
		# TODO : test
		prevblockhash = cd.prevblocks[0]
		if prevblockhash == 0:
			prevsigmadiff = BANT(0)
		else:
			prevblocklist = self.db.getEntry(prevblockhash)
			prevChaindata = Chaindata(self.db.getEntry(prevblocklist[1])) # each GPDHT block has 2nd entry as Chaindata hash
			prevsigmadiff = prevChaindata.sigmadiff
		target = cd.unpackedTarget
		diff = self._target1 // target
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
		self.rawlist = cd[:]
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
