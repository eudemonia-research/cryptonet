

#==============================================================================
# CONST
#==============================================================================

ZERO = chr(0)

#==============================================================================
# LOGIC
#==============================================================================

def xor_strings(xs, ys):
    return "".join(chr(ord(x) ^ ord(y)) for x, y in zip(xs, ys))
	
	
#==============================================================================
# DATA TYPES
#==============================================================================


def s2i(s):
    return long(s.encode('hex'), 16)
    
def i2s(i):
	return i2h(i).decode('hex')
	
def i2h(i):
	assert i >= 0
	h = i.__format__('x')
	return '0'*(len(h)%2)+h
	
	
def sumSI(s,i): return i2s(s2i(s)+i)
def sumIS(i,s): return i2s(s2i(s)+i)
	
def sumSS(s1,s2): return i2s(s2i(s1)+s2i(s2))

def sGT(s1, s2): return s2i(s1) > s2i(s2)

def num2bits(n, minlen=0):
	n = int(n)
	r = []
	while n > 0:
		r.append(n%2)
		n /= 2
	pad = minlen - len(r)
	while pad > 0:
		r.append(0)
		pad -= 1
	return r[::-1]
	
	
def strlist(l):
	return [str(i) for i in l]
	
	
#==============================================================================
# CRYPTO
#==============================================================================

from hashlib import sha256

def sha256Hash(plaintext):
	return sha256(plaintext).digest()
	


#==============================================================================
# NETWORK
#==============================================================================

def packTarget(upt):
	pad = 0
	zero = chr(0)
	while upt[0] == chr(0):
		pad += 1
		upt = upt[1:]
	return upt[:3]+chr(pad)
	
def unpackTarget(pt):
	pt = str(pt)
	pad = ord(pt[3])
	zero = chr(0)
	sigfigs = pt[:3]
	rt = zero*pad + sigfigs + zero*(32-3-pad)
	return long(rt.encode('hex'),16)
	
	
	

#==============================================================================
# THREADING
#==============================================================================
	
import threading

class ThreadWithArgs(threading.Thread):
	def __init__(self, target, *args):
		self.target = target
		self.args = args
		threading.Thread.__init__(self)
		
	def run(self):
		self.target(*self.args)



#==============================================================================
# HTTP
#==============================================================================
	
import requests


def goGetHTTP(node, path, payload={}, method="POST"):
	url = "http://%s:%d%s" % (node.ip, node.port, path)
	if method == "POST":
		r = requests.post(url, data=payload, proxies={"http":""})
	else:
		r = requests.get(url, proxies={"http":""})
	print 'goGetHTTP:', repr(r.text)
	return r.text

def fireHTTP(node, path, payload={}, method="POST"):
	t = ThreadWithArgs(goGetHTTP, node, path, payload, method)
	t.start()
	


#==============================================================================
# JSON HELPER
#==============================================================================

"""Module that monkey-patches json module when it's imported so
JSONEncoder.default() automatically checks for a special "to_json()"
method and uses it to encode the object if found.
-- Found on stack exchange
User: martineau
URL: http://stackoverflow.com/questions/18478287/making-object-json-serializable-with-regular-encoder
"""
import json

def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)

_default.default = json.JSONEncoder().default # save unmodified default
json.JSONEncoder.default = _default # replacement



