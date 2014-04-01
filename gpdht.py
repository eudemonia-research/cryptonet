#!/usr/bin/python

'''gpdht.py contains functions to validate the protocol'''

import hashlib

from datastructs import *

def validPoW(ht, cd):
	return ht.getHash() < cd.unpackedTarget
	
def ghash(msg):
	''' This is the hash function that should be used EVERYWHERE in GPDHT.
	Currently defined to be SHA3.
	As always, should return a BANT '''
	return BANT(hashlib.sha3_256(bytes(msg)).digest())
