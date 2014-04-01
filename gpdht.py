#!/usr/bin/python

'''gpdht.py contains functions to validate the protocol'''

import hashlib
import sha3

from datastructs import *
from utilities import *

def validPoW(ht, cd):
	return ht.getHash() < cd.unpackedTarget
	
