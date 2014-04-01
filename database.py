#!/usr/bin/python

class Database:
	''' in-memory database for testing gracht '''
	def __init__(self):
		''' everything stored in self.d.
		all keys should be hashes and all values should be lists '''
		self.d = {}

	def exists(self, key):
		return key in self.d
	
	def dumpTree(self, tree):
		self.d[tree.getHash()] = tree.leaves()
		
	def dumpChaindata(self, cd):
		self.d[cd.getHash()] = cd.rawlist
		
	def getEntry(self, key):
		return self.d[key]
		
	def setAncestors(self, tree, prevblock):
		pass
