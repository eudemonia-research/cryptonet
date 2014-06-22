import hashlib
import sys
import sha3
import time
import pprint as pprint_module
from binascii import hexlify, unhexlify

import cryptonet
from cryptonet.debug import debug
from cryptonet.errors import ChainError, ValidationError

#==============================================================================
# GENERAL CRYPTONET FUNCTIONS
#==============================================================================

def i2b(x):
    """
    Take and integer and return bytes with no \x00 padding.
    :param x: input integer
    :return: bytes
    """
    return x.to_bytes((x.bit_length() - 1) // 8 + 1, 'big')


def num2bits(n, minlen=0):
    n = int(n)
    r = []
    while n > 0:
        r.append(n % 2)
        n //= 2
    pad = minlen - len(r)
    while pad > 0:
        r.append(0)
        pad -= 1
    return r[::-1]

def random_peer(p2p):
    p2p.peers()

def global_hash(msg, length=None):
    ''' This is the hash function that should be used EVERYWHERE in GPDHT.
    Currently defined to be SHA3.
    Returns int, should accept int'''
    s = hashlib.sha3_256()
    if not isinstance(msg, int):
        s.update(bytes(msg))
    else:
        if length == None:
            length = msg.bit_length() // 8 + 1
        s.update(msg.to_bytes(length, 'big'))
    return int.from_bytes(s.digest(), 'big')

def dsha256R(msg):
    ''' Return a dsha256 hash reversed
    '''
    return dsha256(msg)[::-1]

def dsha256(msg):
    ''' Input should be bytes
    '''
    return sha256(sha256(msg))

def sha256(msg):
    s = hashlib.sha256()
    s.update(msg)
    return s.digest()

def _split_varint_and_bytes(int_location, bytes):
    return (bytes[int_location[0]:int_location[1]], bytes[int_location[1]:])

def get_varint_and_remainder(bytes):
    if bytes[0] < 0xfd:
        return _split_varint_and_bytes((0, 1), bytes)
    if bytes[0] == 0xfd:
        return _split_varint_and_bytes((1, 3), bytes)
    if bytes[0] == 0xfe:
        return _split_varint_and_bytes((1, 5), bytes)
    if bytes[0] == 0xff:
        return _split_varint_and_bytes((1, 9), bytes)


time_as_int = lambda: int(time.time())


def create_index(labels):
    # starts at 1
    dict(zip(labels, [i+1 for i in range(len(labels))]))

pp = pprint_module.PrettyPrinter(indent=4)
def pretty_string(obj):
    return pp.pformat(obj)