import time
import threading

from constants import *
from utilities import debug

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
        
    def addBlock(self, tree, chaindata, uncles=[]):
        h = tree.getHash()
        if h in self.done: return
        if h in self.past: return
        if h not in self.all:
            self.all.add(h)
        with self.past_lock:
            if chaindata.height not in self.pastByHeight: self.pastByHeight[chaindata.height] = [h]
            else: self.pastByHeight[chaindata.height].append(h)
            
            block = [tree, chaindata, uncles]
            if h in self.pastFullBlocks: self.pastFullBlocks[h].append(block)
            self.pastFullBlocks[h] = [block]
            self.past.add(h)
            
    def addBlocksToSeek(self, blockhashes):
        with self.future_lock:
            for bh in blockhashes:
                if bh not in self.all:
                    self.future.add(bh)
                    self.all.add(bh)
        
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
                success = False
                with self.past_lock, self.done_lock:
                    heights = list(self.pastByHeight.keys())
                    assert len(heights) != 0
                    heights.sort()
                    
                    i = 0
                    while heights[i] <= self.chain.headChaindata.height + 1:
                        height = heights[i]
                        if height in self.pastByHeight:
                            blocksToAdd = self.pastByHeight[height]
                            for bh in blocksToAdd:
                                for block in self.pastFullBlocks[bh]:
                                    if not self.chain.hasBlock(bh):
                                        success = self.chain.addBlock(block[BM['hashtree']], block[BM['chaindata']])
                                        height = block[BM['chaindata']].height
                                        self.pastByHeight[height].remove(bh)
                                        if self.pastByHeight[height] == []: del(self.pastByHeight[height])
                                        self.pastFullBlocks[bh].remove(block)
                                        self.past.remove(bh)
                                        self.done.add(bh)
                                        if success:
                                            debug('chainBuilder: broadcasting\n\n')
                                            self.gracht.broadcast(b'blocks', [[block[0].leaves(), block[1].rawlist, []]])
                        i += 1
                        if i >= len(heights): break
                                    
            else:
                time.sleep(0.1)
