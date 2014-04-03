import threading

from gpdht import *
from datastructs import *

class Miner:
	def __init__(self, chain):
		self.shutdown = False
		self.threads = [threading.Thread(target=self.mine)]
		self.chain = chain
		
	def start(self):
		for t in self.threads:
			t.start()
		
	def stop(self):
		self.shutdown = True
		
	def mine(self):
		while not self.shutdown:
			chaindata = self.chain.chaindataTemplate()	
			target = chaindata.unpackedTarget
			message = BANT("It was a bright cold day in April, and the clocks were striking thirteen.")
			nonce = message.getHash()+1
			potentialTree = [self.chain.appid, chaindata.getHash(), message.getHash(), nonce]
			h = HashTree(potentialTree)
			count = 0
			while not self.shutdown:
				count += 1
				h.update(3, nonce)
				PoW = h.getHash()
				if PoW < target:
					break
				nonce += 1
				if count % 10000 == 0:
					debug("Mining block %d : %d : %s" % (int(chaindata.height), count, PoW.hex()))
			if self.shutdown: break
			debug('Miner: Found Soln : %s' % PoW.hex())
			self.chain.addBlock(h, chaindata)
