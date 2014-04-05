import threading
import time

from gpdht import *
from datastructs import *

class Miner:
    def __init__(self, chain, seeknbuild):
        self.shutdown = False
        self.restart = True
        self.threads = [threading.Thread(target=self.mine)]
        self.chain = chain
        self.seeknbuild = seeknbuild
        
    def start(self):
        for t in self.threads:
            t.start()
        
    def stop(self):
        self.shutdown = True
        
    def restart(self):
        self.restart = True
        
    def mine(self):
        while not self.shutdown:
            chaindata = self.chain.chaindataTemplate()  
            target = chaindata.unpackedTarget
            message = BANT("It was a bright cold day in April, and the clocks were striking thirteen.")
            with open('/dev/urandom', 'br') as r:
                nonce = BANT(bytes(r.read(32)))
            potentialTree = [self.chain.appid, chaindata.getHash(), message.getHash(), nonce]
            h = HashTree(potentialTree)
            count = 0
            debug("Miner running on block #%d" % chaindata.height)
            while not self.shutdown:
                count += 1
                h.update(3, nonce)
                PoW = h.getHash()
                if PoW < target:
                    break
                nonce += 1
                if count % 100 == 0:
                    if self.restart: break
                    if count % 100000 == 0:
                        self.restart = True
            if self.shutdown: break
            if self.restart: 
                debug('Miner restarting')
                self.restart = False
                continue
            debug('Miner: Found Soln : %s' % PoW.hex())
            #self.chain.addBlock(h, chaindata) - no no no
            self.seeknbuild.addBlock(h, chaindata)
            while not self.chain.hasBlock(PoW):
                time.sleep(0.03)
