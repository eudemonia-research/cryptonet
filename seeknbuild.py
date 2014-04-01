#!/usr/bin/python3

import time
import threading

MAX_BLOCKS_AT_ONCE = 1000

class SeekNBuild:
	def __init__(self, gracht):
		self.gracht = gracht
		
		self.future = set()
		self.present = set()
		self.past = set()
		self.chain = set()
		self.all = set()
		self.shutdown = False
		
		self.presentLastRequest = {} # should be {hash:timestamp}
		self.pastByHeight = {} 
		
		self.future_semaphore = threading.BoundedSemaphore()
		self.present_semaphore = threading.BoundedSemaphore()
		self.past_semaphore = threading.BoundedSemaphore()
		self.chain_semaphore = threading.BoundedSemaphore()
		self.all_semaphore = threading.BoundedSemaphore()
		
	def blockSeeker(self):
		while not self.shutdown:
			self.future_semaphore.acquire()
			self.present_semaphore.acquire()
			
			allFuture = len(self.future)
			toGet = min(allFuture, MAX_BLOCKS_AT_ONCE)
			requesting = []
			for i in range(toGet):
				h = self.future.pop()
				requesting.append(h)
				self.present.add(h)
				self.presentLastRequest[h] = int(time.time())
				
			if toGet == 0:
				# TODO : re-request from self.present if time > a few seconds
				pass
				
			self.future_semaphore.release()
			self.present_semaphore.release()
			
			# TODO : don't broadcast to all nodes, just one
			self.gracht.broadcast(b'requestblocks', requesting)
			
			time.sleep(0.1)
			
	def chainBuilder(self):
		while not self.shutdown:
			
			
			
			time.sleep(0.1)
