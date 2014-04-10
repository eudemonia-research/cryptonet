from cryptonet.gpdht import *
from cryptonet import rlp
import math

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
            # p0.hash ++ p1.hash
            concat = lambda x: self.children[x[0]].getHash().concat(self.children[x[1]].getHash())
            if len(self.children) == 1: self.myhash = ghash(concat([0,0]))
            else: self.myhash = ghash(concat([0,1]))
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
        
        
class MerkleTree:
    # TODO : take out TTL stuff, and rename to something that makes sense.
    def __init__(self, init):
        assert len(init) > 0
        self.n = len(init)
        self.leaves = init[:]
        
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
        
        
    def genLeaves(self):
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
        return self.leaves[pos]
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


#============================
# ChainVars
#============================

class ChainVars:
    def __init__(self, **kwargs):
        pass
            
            
#============================
# Messages
#============================

class Intro:
    def __init__(self, rawlist=None, topblock=None):
        self.topblock = topblock
        self.rawlist = [topblock]*8
        
        if rawlist != None:
            self.rawlist = rawlist
            self.fromList(rawlist)
    def fromList(self, l):
        self.topblock = l[7]
    def deserialize(self, ser):
        self.fromList(rlp.deserialize(ser))
        return self
    def serialize(self):
        return rlp.serialize(self.rawlist)
    def getHash(self):
        return ghash(self.serialize())
