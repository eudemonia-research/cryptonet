import time
import threading

MAX_BLOCKS_AT_ONCE = 1000

class SeekNBuild:
	def __init__(self, gracht, chain):
		self.gracht = gracht
		self.chain = chain
		
		self.future = set()
		self.present = set()
		self.past = set()
		self.done = set()
		self.all = set()
		self.shutdown = False
		
		self.presentLastRequest = {} # should be {hash:timestamp}
		self.pastByHeight = {} # {height:[hash]} - maybe use DB
		self.pastFullBlocks = {} # {hash:block}
		
		self.future_lock = threading.Lock()
		self.present_lock = threading.Lock()
		self.past_lock = threading.Lock()
		self.done_lock = threading.Lock()
		self.all_lock = threading.Lock()
		
		# start blockSeeker and chainBuilder threads
		self.threads = [threading.Thread(target=self.blockSeeker), threading.Thread(target=self.chainBuilder)]
		for t in self.threads: t.start()
		
	def stop(self):
		self.shutdown = True
		
	def blockSeeker(self):
		while not self.shutdown:
			requesting = []
			with self.future_lock, self.present_lock:
				allFuture = len(self.future)
				toGet = min(allFuture, MAX_BLOCKS_AT_ONCE)
				
				for i in range(toGet):
					h = self.future.pop()
					requesting.append(h)
					self.present.add(h)
					self.presentLastRequest[h] = int(time.time())
					
				if toGet == 0:
					# TODO : re-request from self.present if time > a few seconds
					pass
			
			if len(requesting) > 0:
				# TODO : don't broadcast to all nodes, just one
				self.gracht.broadcast(b'requestblocks', requesting)
			
			time.sleep(0.1)
			
	def chainBuilder(self):
		''' This should find all blocks in s.past with a height <= chain_height + 1 and
		add them to the main chain '''
		while not self.shutdown:
			if len(self.past) > 0:
				with self.past_lock, self.done_lock:
					heights = self.pastByHeight.keys()
					heights.sort()
					
					i = 0
					while heights[i] <= self.chain.head.height + 1:
						height = heights[i]
						if height in self.pastByHeight:
							blocksToAdd = self.pastByHeight[height]
							for bh in blocksToAdd:
								if self.chain.hasBlock(bh):
									b = self.pastFullBlocks[bh]
									self.chain.addBlock(*b)
									self.past.remove(bh)
									self.done.add(bh)
									
			else:
				time.sleep(0.1)
