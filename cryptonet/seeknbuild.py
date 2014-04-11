import time
import threading
import queue

from cryptonet.gpdht import *
from cryptonet.errors import *
from cryptonet.debug import *

from cryptonet.datastructs import *

from encodium import *

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
    blocks, and facilitate the Chain object finding the longest PoW chain possible. '''
    def __init__(self, p2p, chain):
        self.p2p = p2p
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
        
        self._funcs = {
            'height': self.chain.getHeight,
        }
        
        self.threads = [threading.Thread(target=self.blockSeeker), threading.Thread(target=self.chainBuilder)]
        for t in self.threads: t.start()
        
        
    def max_blocks_at_once(self):
        return int(max(5, min(500, self.getChainHeight()) // 3))
        
    def shutdown(self):
        self._shutdown = True
        for t in self.threads:
            t.join()
        
    def addBlock(self, block):
        bh = block.getHash()
        toPut = (block.height, self.nonces.getNext(), block)
        
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
            
    def seekHash(self, bh):
        with self.future_lock:
            self.futureQueue.put((-1, bh))
            self.future.add(bh)
        
    def seekWithPriority(self, blockhashWithHeight):
        h = blockhashWithHeight[0]
        bh = blockhashWithHeight[1]
        if bh not in self.all:
            self.all.add(bh)
            with self.future_lock:
                self.futureQueue.put((h, bh))
                self.future.add(bh)
                    
    def seekManyWithPriority(self, blockhashesWithHeight):
        for h, bh in blockhashesWithHeight:
            self.seekWithPriority((h, bh))
        
    def blockSeeker(self):
        while not self._shutdown and not self.chain.initialized: time.sleep(0.1)
        while not self._shutdown:
            # we will eventually serialize this so we make it a Field
            requesting = List(Integer(length=32), default=[]).make()
            
            try:
                with self.present_lock:
                    oldestTS, oldestBH = self.presentQueue.get_nowait()
                    while oldestTS + 10 < time.time(): # requested >10s ago
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
                        #print('blockSeeker: asking for height: ',_)
                        self.future.remove(h)
                        if _ != 0:
                            requesting.append(h)
                
                for h in requesting:
                    with self.present_lock:
                        self.presentQueue.put((int(time.time()), h))
                        self.present.add(h)
            
            if len(requesting) > 0:
                # TODO : don't broadcast to all nodes, just one
                #self.p2p.broadcast('requestblocks', ALL_BYTES(requesting))
                somepeer = self.p2p.random_peer()
                while True:
                    # ordered carefully
                    if somepeer == None or ('lastmessage' in somepeer.data and somepeer.data['lastmessage'] + 0.2 > time.time()):
                        time.sleep(0.01)
                        somepeer = self.p2p.random_peer()
                    else:
                        break
                somepeer.send('requestblocks', requesting.serialize())
                somepeer.data['lastmessage'] = time.time()
            else:
                time.sleep(0.1)
    
    def getChainHeight(self):
        return self._funcs['height']()
        
    def chainBuilder(self):
        ''' This should find all blocks in s.past with a height <= chain_height + 1 and
        add them to the main chain '''
        while not self._shutdown and not self.chain.initialized: time.sleep(0.1)
        while not self._shutdown:
            try:
                height, nonce, block = self.pastQueue.get(timeout=0.1)
            except queue.Empty:
                continue
            if block.height == 0:
                continue
            bh = block.getHash()
            #print('chainbuilder: checking %d' % block.height)
            
            # TODO : handle orphans intelligently
            if block.height > self.getChainHeight() + 1:
                #print('chainbuilder: chain height: %d' % self.getChainHeight())
                #print('chainbuilder: block.height %d' % block.height)
                self.pastQueue.put((height, nonce, block))
                # try some of those which were parentless:
                with self.past_lock:
                    while not self.pastQueueNoParent.empty():
                        self.pastQueue.put(self.pastQueueNoParent.get())
                time.sleep(0.05)
            else:
                if self.chain.hasBlock(bh):
                    try:
                        self.past.remove(bh)
                    except KeyError:
                        pass
                    self.done.add(bh)
                    continue
                # TODO : handle orphans intelligently
                if not self.chain.hasBlockhash(block.parenthash):
                    #print('chainbuilder: dont have parent')
                    #print('chainbuilder: head and curr', self.chain.head.getHash().hex(), block.parenthash.hex())
                    self.pastQueueNoParent.put((height, nonce, block))
                    continue
                try:
                    block.assertValidity(self.chain)
                except ValidationError as e:
                    # invalid block
                    print('chainbuidler validation error: ', e)
                    continue
                success = self.chain.addBlock(block)
                self.past.remove(bh)
                self.done.add(bh)
                if success:
                    toSend = BlockList.make(blocklist = [block.serialize()])
                    self.p2p.broadcast('blocks', toSend.serialize())
            
            
