import threading
import time

from cryptonet.debug import *

class Miner:
    def __init__(self, chain, seeknbuild):
        self._shutdown = False
        self._restart = False
        self.threads = [threading.Thread(target=self.mine)]
        self.chain = chain
        self.chain.setMiner(self)
        self.seeknbuild = seeknbuild
        
    def run(self):
        for t in self.threads:
            t.start()
        
    def shutdown(self):
        self._shutdown = True
        for t in self.threads:
            t.join()
        
    def restart(self):
        self._restart = True
        
    def mine(self, providedBlock=None):
        while not self._shutdown:
            if providedBlock == None: block = self.chain.head.getCandidate(self.chain)
            else: 
                block = providedBlock
                providedBlock = None
            count = 0
            print('miner restarting')
            while not self._shutdown and not self._restart:
                count += 1
                block.incrementNonce()
                if block.validPoW():
                    break
                if count % 100000 == 0:
                    self._restart = True
            if self._shutdown: break
            if self._restart: 
                self._restart = False
                time.sleep(0.01)
                continue
            debug('Miner: Found Soln : %064x' % block.getHash())
            debug('Miner: ser\'d block: ', block.serialize())
            self.seeknbuild.addBlock(block)
            while not self.chain.hasBlockhash(block.getHash()) and not self._shutdown:
                time.sleep(0.1)
