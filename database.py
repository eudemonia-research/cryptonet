#!/usr/bin/python

class Database:
	''' in-memory database for testing gracht '''
	def __init__(self):
		''' everything stored in self.d.
		all keys should be hashes and all values should be lists '''
		self.d = {}

	def exists(self, key):
		return key in self.d
