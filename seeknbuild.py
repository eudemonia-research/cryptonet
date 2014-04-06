import time
import threading
import queue

from constants import *
from utilities import debug
from gpdht import *
from datastructs import *

class AtomicIncrementor:
    def __init__(self):
        self.lock = threading.Lock()
        self.counter = 0
    def getNext(self):
        with self.lock:
            r = self.counter
            self.counter += 1
        return r

class SeekNBuild:
    ''' The SeekNBuild class is responsible for attempting to acquire all known
    blocks, and build the longest PoW chain possible. '''
    def __init__(self, gracht, chain):
        self.gracht = gracht
        self.chain = chain
        
        self.nonces = AtomicIncrementor()
        
        self.future = set()
        self.futureQueue = queue.PriorityQueue()
        self.present = set()
        self.presentQueue = queue.PriorityQueue()
        self.past = set()
        self.pastQueue = queue.PriorityQueue()
        self.pastQueueNoParent = queue.PriorityQueue()
        self.done = set()
        self.all = set()
        self._shutdown = False
        
        self.future_lock = threading.Lock()
        self.present_lock = threading.Lock()
        self.past_lock = threading.Lock()
        
        self.threads = [threading.Thread(target=self.blockSeeker), threading.Thread(target=self.chainBuilder)]
        for t in self.threads: t.start()
        
    def max_blocks_at_once(self):
        return int(max(5, min(500, self.chain.headChaindata.height) // 3))
        
    def shutdown(self):
        self._shutdown = True
        for t in self.threads:
            t.join()
        
    def addBlock(self, tree, chaindata, uncles=[]):
        bh = tree.getHash()
        block = [tree, chaindata, uncles]
        # without nonce, if we add toPut to pastQueue and there is another entry with identical
        # height, it will attempt to compare blocks (which is a list) as they are next in the tuple (after the equal heights).
        # This means comparison will next operate on HashTrees, which are not comparible.
        toPut = (chaindata.height, self.nonces.getNext(), block)
        
        if bh in self.done: return
        if bh in self.past: return
        
        if bh not in self.all:
            self.all.add(bh)
        
        with self.present_lock:
            try:
                self.present.remove(bh)
            except KeyError:
                pass
        
        with self.past_lock:
            self.past.add(bh)
            self.pastQueue.put(toPut)
        
    def addBlocksToSeek(self, blockhashesWithHeight):
        for h, bh in blockhashesWithHeight:
            if bh not in self.all:
                self.all.add(bh)
                with self.future_lock:
                    self.futureQueue.put((h, bh))
                    self.future.add(bh)
        
    def blockSeeker(self):
        while not self._shutdown:
            requesting = []
            
            # TODO : re-request from self.present if time > a few seconds
            # oldest request will be pulled first
            # present.get() -> (timeinserted, hash)
            # ensure hash in self.present(), if not go to top
            # if timeinserted < time.time() + 10, reinsert
            # otherwise, check if hash is in done or past, if not, re-request and re-insert with new time
            # go to top
            
            try:
                with self.present_lock:
                    oldestTS, oldestBH = self.presentQueue.get_nowait()
                    while oldestTS + 20 < time.time(): # requested >20s ago
                        if oldestBH in self.present:
                            requesting.append(oldestBH)
                        oldestTS, oldestBH = self.presentQueue.get_nowait()
                    self.presentQueue.put((oldestTS, oldestBH))
            except queue.Empty:
                pass
            
            with self.future_lock:
                toGet = min(len(self.future), self.max_blocks_at_once()) - len(requesting)
                if toGet > 0: # pick some blocks to request
                    for i in range(toGet):
                        _, h = self.futureQueue.get()
                        print('blockSeeker: asking for height: ',_)
                        self.future.remove(h)
                        requesting.append(h)
                
                for h in requesting:
                    with self.present_lock:
                        self.presentQueue.put((int(time.time()), h))
                        self.present.add(h)
            
            if len(requesting) > 0:
                # TODO : don't broadcast to all nodes, just one
                #self.gracht.broadcast('requestblocks', ALL_BYTES(requesting))
                somepeer = self.gracht.random_peer()
                while True:
                    # ordered carefully
                    if somepeer == None or ('lastmessage' in somepeer.data and somepeer.data['lastmessage'] + 0.2 > time.time()):
                        time.sleep(0.01)
                        somepeer = self.gracht.random_peer()
                    else:
                        break
                somepeer.send('requestblocks', ALL_BYTES(requesting))
                somepeer.data['lastmessage'] = time.time()
            else:
                time.sleep(0.1)
            
    def chainBuilder(self):
        ''' This should find all blocks in s.past with a height <= chain_height + 1 and
        add them to the main chain '''
        while not self._shutdown:
            try:
                height, nonce, block = self.pastQueue.get(timeout=0.5)
            except queue.Empty:
                continue
            bh = block[0].getHash()
            
            if height > self.chain.headChaindata.height + 1:
                self.pastQueue.put((height, nonce, block))
                # try some of those which were parentless:
                if self.pastQueueNoParent.empty():
                    time.sleep(0.05)
                while not self.pastQueueNoParent.empty():
                    self.pastQueue.put(self.pastQueueNoParent.get())
            else:
                # TODO: if chain doesn't have parent block put to the side for a bit, but don't throw away
                if not self.chain.hasBlock(block[BM['chaindata']].prevblocks[0]):
                    self.pastQueueNoParent.put((height, nonce, block))
                    continue
                if self.chain.hasBlock(bh):
                    try:
                        self.past.remove(bh)
                    except KeyError:
                        pass
                    self.done.add(bh)
                    continue
                success = self.chain.addBlock(block[BM['hashtree']], block[BM['chaindata']], block[BM['uncles']])
                self.past.remove(bh)
                self.done.add(bh)
                if success:
                    self.gracht.broadcast('blocks', ALL_BYTES([[block[0].leaves(), block[1].rawlist, []]]))
            
            
