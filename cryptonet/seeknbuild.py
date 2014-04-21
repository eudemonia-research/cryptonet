import time
import queue
#import threading

from cryptonet.datastructs import *


class AtomicIncrementor:
    def __init__(self):
        self.lock = threading.Lock()
        self.counter = 0
    def get_next(self):
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
        self.future_queue = queue.PriorityQueue()
        self.present = set()
        self.present_queue = queue.PriorityQueue()
        self.past = set()
        self.past_queue = queue.PriorityQueue()
        self.past_queue_no_parent = queue.PriorityQueue()
        self.done = set()
        self.all = set()
        self._shutdown = False
        
        self.future_lock = threading.Lock()
        self.present_lock = threading.Lock()
        self.past_lock = threading.Lock()
        
        self._funcs = {
            'height': self.chain.get_height,
        }
        
        self.threads = [threading.Thread(target=self.block_seeker), threading.Thread(target=self.chain_builder)]
        for t in self.threads: 
            t.start()
        
        
    def max_blocks_at_once(self):
        return int(max(5, min(500, self.get_chain_height()) // 3))
        
    def shutdown(self):
        self._shutdown = True
        for t in self.threads:
            t.join()
        
    def add_block(self, block):
        # blocks should be internally consistent at this point
        bh = block.get_hash()
        toPut = (block.height, self.nonces.get_next(), block)
        
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
            self.past_queue.put(toPut)
            
    def seek_hash(self, bh):
        with self.future_lock:
            self.future_queue.put((-1, bh))
            self.future.add(bh)
        
    def seek_with_priority(self, block_hash_with_height):
        h = block_hash_with_height[0]
        bh = block_hash_with_height[1]
        if bh not in self.all:
            self.all.add(bh)
            with self.future_lock:
                self.future_queue.put((h, bh))
                self.future.add(bh)
                    
    def seek_many_with_priority(self, block_hashes_with_height):
        for h, bh in block_hashes_with_height:
            self.seek_with_priority((h, bh))
        
    def block_seeker(self):
        while not self._shutdown and not self.chain.initialized: 
            time.sleep(0.1)
        while not self._shutdown:
            # we will eventually serialize this so we make it a Field
            requesting = IntList.make()
            
            try:
                with self.present_lock:
                    oldestTS, oldestBH = self.present_queue.get_nowait()
                    while oldestTS + 10 < time.time(): # requested >10s ago
                        if oldestBH in self.present:
                            requesting.append(oldestBH)
                        oldestTS, oldestBH = self.present_queue.get_nowait()
                    self.present_queue.put((oldestTS, oldestBH))
            except queue.Empty:
                pass
            
            with self.future_lock:
                toGet = min(len(self.future), self.max_blocks_at_once()) - requesting.len()
                if toGet > 0: 
                    # pick some blocks to request
                    for i in range(toGet):
                        _, h = self.future_queue.get()
                        #print('block_seeker: asking for height: ',_)
                        self.future.remove(h)
                        if _ != 0:
                            requesting.append(h)
                
                for h in requesting:
                    with self.present_lock:
                        self.present_queue.put((int(time.time()), h))
                        self.present.add(h)
            
            if requesting.len() > 0:
                # TODO : don't broadcast to all nodes, just one
                #self.p2p.broadcast('request_blocks', ALL_BYTES(requesting.hashlist))
                somepeer = self.p2p.random_peer()
                while True:
                    # ordered carefully
                    if somepeer == None:
                        time.sleep(0.01)
                        somepeer = self.p2p.random_peer()
                    else:
                        break
                somepeer.send('request_blocks', requesting.serialize())
                somepeer.data['lastmessage'] = time.time()
            else:
                time.sleep(0.1)
    
    def get_chain_height(self):
        return self._funcs['height']()

    def broadcast_block(self, to_send):
        def real_broadcast(self, to_send):
            self.p2p.broadcast('blocks', to_send.serialize())
        t = threading.Thread(target=real_broadcast, args=(self, to_send))
        t.start()
        self.threads.append(t)
        
    def chain_builder(self):
        ''' This should find all blocks in s.past with a height <= chain_height + 1 and
        add them to the main chain '''
        while not self._shutdown and not self.chain.initialized: time.sleep(0.1)
        while not self._shutdown:
            try:
                height, nonce, block = self.past_queue.get(timeout=0.1)
                print('builder:',height, nonce, block)
            except queue.Empty:
                continue
            if block.height == 0:
                continue
            bh = block.get_hash()
            #print('chain_builder: checking %d' % block.height)
            debug('builder: checkpoint 1')
            # TODO : handle orphans intelligently
            if block.height > self.get_chain_height() + 1:
                #print('chain_builder: chain height: %d' % self.get_chain_height())
                #print('chain_builder: block.height %d' % block.height)
                self.past_queue.put((height, nonce, block))
                # try some of those which were parentless:
                with self.past_lock:
                    while not self.past_queue_no_parent.empty():
                        self.past_queue.put(self.past_queue_no_parent.get())
                time.sleep(0.05)
            else:
                if self.chain.has_block(bh):
                    try:
                        self.past.remove(bh)
                    except KeyError:
                        pass
                    self.done.add(bh)
                    continue
                # TODO : handle orphans intelligently
                if not self.chain.has_block_hash(block.parent_hash):
                    print('chain_builder: dont have parent')
                    print('chain_builder: head and curr', self.chain.head.get_hash(), block.parent_hash)
                    self.past_queue_no_parent.put((height, nonce, block))
                    continue
                try:
                    block.assert_validity(self.chain)
                except ValidationError as e:
                    # invalid block
                    print('chainbuidler validation error: ', e)
                    continue
                self.chain.add_block(block)
                self.past.remove(bh)
                self.done.add(bh)
                debug('builder to send : %064x' % block.get_hash())
                debug('builder to send full : %s' % block.serialize())
                toSend = BytesList.make(contents = [block.serialize()])
                debug('builder sending...')
                self.broadcast_block(block)
                debug('builder success : %064x' % block.get_hash())
        
            
