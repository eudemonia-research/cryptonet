import threading
import time

from cryptonet.debug import debug
from cryptonet.errors import ValidationError

class Miner:
    def __init__(self, chain, seek_n_build):
        self._shutdown = False
        self._restart = False
        self.threads = [threading.Thread(target=self.mine)]
        self.chain = chain
        self.chain.set_miner(self)
        self.seek_n_build = seek_n_build
        
    def run(self):
        for t in self.threads:
            t.start()
        
    def shutdown(self):
        self._shutdown = True
        for t in self.threads:
            t.join()
        
    def restart(self):
        self._restart = True
        
    def mine(self, provided_block=None):
        while not self._shutdown:
            # TODO: Temporary
            time.sleep(0.1)
            if provided_block == None: block = self.chain.head.get_candidate(self.chain)
            else: 
                block = provided_block
                provided_block = None
            count = 0
            print('miner restarting')
            while not self._shutdown and not self._restart:
                count += 1
                block.increment_nonce()
                if block.valid_proof_of_work():
                    try:
                        block.assert_internal_consistency()
                        break
                    except ValidationError as e:
                        debug('Miner: invalid block generated: %s' % block.serialize())
                        continue
                if count % 100000 == 0:
                    self._restart = True
            if self._shutdown: break
            if self._restart: 
                self._restart = False
                time.sleep(0.01)
                continue
            debug('Miner: Found Soln : %064x' % block.get_hash())
            if block.height == 0 or True:
                debug('Miner: ser\'d block: ', block.serialize())
            self.seek_n_build.add_block(block)
            while not self.chain.has_block_hash(block.get_hash()) and not self._shutdown:
                time.sleep(0.1)
