'''gpdht.py contains functions to validate the protocol'''

import hashlib, sys
import sha3
from binascii import hexlify, unhexlify

import cryptonet
from cryptonet.debug import debug
from cryptonet.errors import ChainError

#from utilities import *



'''
def pack_target(unpacked_target):
    # TODO : test
    pad = 32 - len(unpacked_target)
    while unpacked_target[0] == 0:
        pad += 1
        unpacked_target = unpacked_target[1:]
    a = unpacked_target[:3] + bytearray([pad])
    return BANT(a)
    
def unpack_target(packed_target):
    # TODO : test
    packed_target = bytes(packed_target)
    pad = packed_target[3]
    sigfigs = packed_target[:3]
    rt = ZERO*pad + sigfigs + ZERO*(32-3-pad)
    return BANT(int(hexlify(rt),16))
'''

