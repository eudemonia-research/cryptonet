import hashlib, sys
import sha3
from binascii import hexlify, unhexlify

import cryptonet
from cryptonet.debug import debug
from cryptonet.errors import ChainError

#==============================================================================
# GENERAL CRYPTONET FUNCTIONS
#==============================================================================

def i2b(x):
    """
    Take and integer and return bytes with no \x00 padding.
    :param x: input integer
    :return: bytes
    """
    return x.to_bytes((x.bit_length() // 8) + 1, 'big')

def num2bits(n, minlen=0):
    n = int(n)
    r = []
    while n > 0:
        r.append(n%2)
        n //= 2
    pad = minlen - len(r)
    while pad > 0:
        r.append(0)
        pad -= 1
    return r[::-1]

def global_hash(msg):
    ''' This is the hash function that should be used EVERYWHERE in GPDHT.
    Currently defined to be SHA3.
    As always, should return a BANT '''
    s = hashlib.sha3_256()
    s.update(bytes(msg))
    return int.from_bytes(s.digest(), 'big')
