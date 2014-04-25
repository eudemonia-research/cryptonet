import time
import queue
#import threading

from cryptonet.datastructs import *
from cryptonet.errors import ValidationError

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
    blocks, and facilitate the Chain object finding the longest PoW chain possible.

    See the block_seeker and chain_builder functions for more info.
    '''
    def __init__(self, p2p, chain):
        self.p2p = p2p
        self.chain = chain
        self.chain.learn_of_seek_n_build(self)
        
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
        # no reason for special values besides
        return int(max(5, min(500, self.get_chain_height()) // 3))
        
    def shutdown(self):
        self._shutdown = True
        for t in self.threads:
            t.join()
            
    def seek_hash_now(self, block_hash):
        ''' Add block_hash to queue with priority -1 (will be pulled next).
        '''
        if block_hash == 0: return
        if block_hash not in self.all:
            with self.future_lock:
                self.future_queue.put((-1, block_hash))
                self.future.add(block_hash)
        
    def seek_with_priority(self, block_hash_with_height):
        ''' Add block_hash to future queue with its priority.
        '''
        height, block_hash = block_hash_with_height
        if block_hash == 0: return
        if block_hash not in self.all:
            self.all.add(block_hash)
            with self.future_lock:
                self.future_queue.put((height, block_hash))
                self.future.add(block_hash)
                    
    def seek_many_with_priority(self, block_hashes_with_height):
        ''' Applies each in list to seek_with_priority()
        '''
        for height, block_hash in block_hashes_with_height:
            self.seek_with_priority((height, block_hash))
        
    def block_seeker(self):
        ''' block_seeker() should be in its own thread.
        block_seeker will run in a loop and:
        1. Are there any blocks that were requested more than X seconds ago
            1.1 for each block that was, add it to requesting
            1.2 throw it away if it is no longer in the self.preset set
        2. Find the number of blocks to send
            2.1 get that many from the future_queue
        3. For each block_hash to request, add it to the present_queue with the time it was requested.
        4. Pick a random peer and send the request to it.
        '''
        while not self._shutdown and not self.chain.initialized: 
            time.sleep(0.1)
        while not self._shutdown:
            # we will eventually serialize this so we make it a Field
            requesting = IntList.make()
            
            try:
                with self.present_lock:
                    oldest_timestamp, oldest_block_hash = self.present_queue.get_nowait()
                    while oldest_timestamp + 10 < time.time(): # requested >10s ago
                        debug('seeker, block re-request: ', oldest_block_hash)
                        if oldest_block_hash in self.present:
                            requesting.append(oldest_block_hash)
                        oldest_timestamp, oldest_block_hash = self.present_queue.get_nowait()
                    self.present_queue.put((oldest_timestamp, oldest_block_hash))
            except queue.Empty:
                pass
            
            with self.future_lock:
                to_get = min(len(self.future), self.max_blocks_at_once()) - requesting.len()
                if to_get > 0: 
                    # pick some blocks to request
                    for i in range(to_get):
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
                some_peer = self.p2p.random_peer()
                while True:
                    # ordered carefully
                    if some_peer == None:
                        time.sleep(0.01)
                        some_peer = self.p2p.random_peer()
                    else:
                        break
                some_peer.send('request_blocks', requesting.serialize())
                some_peer.data['lastmessage'] = time.time()
            else:
                time.sleep(0.1)
    
    def get_chain_height(self):
        return self._funcs['height']()

    def broadcast_block(self, to_send):
        ''' Forks off to avoid hang if p2p playing up. This should not be needed.
        Thread my be commented out; broadcast may be as normal. (debug)
        '''
        self.p2p.broadcast('blocks', to_send.serialize())
        '''def real_broadcast(self, to_send):
            self.p2p.broadcast('blocks', to_send.serialize())
        t = threading.Thread(target=real_broadcast, args=(self, to_send))
        t.start()
        self.threads.append(t)
        '''

    def add_block(self, block):
        '''
        Add a block to the past_queue (ready for chain_builder) if we haven't done so before.
        '''
        # blocks should be internally consistent at this point
        block_hash = block.get_hash()
        to_put = (block.height, self.nonces.get_next(), block)

        with self.past_lock:
            if block_hash in self.past or block_hash in self.done:
                return
            self.past.add(block_hash)
            self.past_queue.put(to_put)

        self.all.add(block_hash)

        with self.present_lock:
            try:
                self.present.remove(block_hash)
            except KeyError:
                pass
        
    def chain_builder(self):
        '''
        1. Get the next block.
        2. If the block is potentially the next block (or older that the chain head)
            2.1 Check we don't already have it
            2.2 Ensure it's valid
            2.3 Add it to the Chain
            2.4 Broadcast to peers
        '''
        while not self._shutdown and not self.chain.initialized:
            time.sleep(0.1)
        while not self._shutdown:
            try:
                height, nonce, block = self.past_queue.get(timeout=0.1)
                print('builder:',height, nonce, block)
            except queue.Empty:
                continue
            if block.height == 0:
                self.past.remove(block.get_hash())
                self.done.add(block.get_hash())
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
                    print('chain_builder: don\'t have parent')
                    print('chain_builder: head and curr', self.chain.head.get_hash(), block.parent_hash)
                    self.past_queue_no_parent.put((height, nonce, block))
                    continue
                try:
                    block.assert_validity(self.chain)
                except ValidationError as e:
                    # invalid block
                    print('buidler validation error: ', e)
                    continue
                self.chain.add_block(block)
                self.past.remove(bh)
                self.done.add(bh)
                debug('builder to send : %064x' % block.get_hash())
                to_send = BlocksMessage.make(contents = [block.serialize()])
                debug('builder sending...')
                debug('builder to send full : %s' % to_send.serialize())
                self.broadcast_block(to_send)
                debug('builder success : %064x' % block.get_hash())
        
            
