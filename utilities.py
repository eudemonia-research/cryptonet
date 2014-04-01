from binascii import hexlify, unhexlify

#==============================================================================
# DEBUG
#==============================================================================

def debug(msg):
	print(msg)

#==============================================================================
# CONST
#==============================================================================

ZERO = b'\x00'

#==============================================================================
# LOGIC
#==============================================================================

def xor_strings(xs, ys):
    return "".join(chr(ord(x) ^ ord(y)) for x, y in zip(xs, ys))
	
	
#==============================================================================
# DATA TYPES
#==============================================================================


def s2i(s):
    return long(hexlify(s), 16)
    
def i2s(i):
	return unhexlify(i2h(i))
	
def i2h(i):
	assert i >= 0
	h = i.__format__('x').encode()
	return b'0'*(len(h)%2)+h
	
	
def sumSI(s,i): return i2s(s2i(s)+i)
def sumIS(i,s): return i2s(s2i(s)+i)
	
def sumSS(s1,s2): return i2s(s2i(s1)+s2i(s2))

def sGT(s1, s2): return s2i(s1) > s2i(s2)

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
	
	
def strlist(l):
	return [str(i) for i in l]
	


#==============================================================================
# NETWORK
#==============================================================================

def packTarget(upt):
	# TODO : test
	pad = 0
	while upt[0] == ZERO:
		pad += 1
		upt = upt[1:]
	return upt[:3]+chr(pad)
	
def unpackTarget(pt):
	# TODO : test
	pt = bytes(pt)
	pad = pt[3]
	sigfigs = pt[:3]
	rt = ZERO*pad + sigfigs + ZERO*(32-3-pad)
	return int(hexlify(rt),16)
	
	
def packSigmadiff(upsd):
	# TODO : test
	pad = 0
	while upsd[0] == ZERO:
		pad += 1
		upsd = upsd[1:]
	return upsd[:5] + chr(pad)
	
def unpackSigmadiff(psd):
	# TODO : test
	psd = bytes(psd)
	pad = psd[5]
	sigfigs = psd[:5]
	rt = ZERO*pad + sigfigs + ZERO*(32-5-pad)
	return int(hexlify(rt), 16)
	

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

