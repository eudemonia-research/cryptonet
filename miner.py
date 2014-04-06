import threading
import time

from gpdht import *
from datastructs import *

class Miner:
    def __init__(self, chain, seeknbuild):
        self._shutdown = False
        self._restart = True
        self.threads = [threading.Thread(target=self.mine)]
        self.chain = chain
        self.chain.setMiner(self)
        self.seeknbuild = seeknbuild
        
    def start(self):
        for t in self.threads:
            t.start()
        
    def shutdown(self):
        self._shutdown = True
        for t in self.threads:
            t.join()
        
    def restart(self):
        self._restart = True
        
    def mine(self):
        while not self._shutdown:
            chaindata = self.chain.chaindataTemplate()  
            target = chaindata.unpackedTarget
            message = BANT("It was a bright cold day in April, and the clocks were striking thirteen.")
            with open('/dev/urandom', 'br') as r:
                nonce = BANT(bytes(r.read(32)))
            potentialTree = [self.chain.appid, chaindata.getHash(), message.getHash(), nonce]
            h = HashTree(potentialTree)
            count = 0
            debug("Miner running on block #%d" % chaindata.height)
            while not self._shutdown:
                count += 1
                h.update(3, nonce)
                PoW = h.getHash()
                if PoW < target:
                    break
                nonce += 1
                if count % 100 == 0:
                    if self._restart: break
                    if count % 100000 == 0:
                        self._restart = True
            if self._shutdown: break
            if self._restart: 
                debug('Miner restarting')
                self._restart = False
                continue
            debug('Miner: Found Soln : %s' % PoW.hex())
            #self.chain.addBlock(h, chaindata) - no no no
            self.seeknbuild.addBlock(h, chaindata)
            while not self.chain.hasBlock(PoW):
                time.sleep(0.03)
