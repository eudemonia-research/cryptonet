from spore import Spore
#from . import defaultStructures
from cryptonet.seeknbuild import SeekNBuild
from cryptonet.gpdht import *
from cryptonet.database import Database
from cryptonet.errors import *
from cryptonet.datastructs import *

from gpdht import *

config = {'networkdebug':True}

class Cryptonet(object):
    def __init__(self, chainVars):
        self._Block = None
        
        self.p2p = Spore(seeds=chainVars.seeds)
        self.setHandlers()
        print(self.p2p.peers)
        
        self.db = Database()
        self.chain = Chain(chainVars, db=self.db)
        self.miner = None
        #self.miner = Miner(chain)
        self.seekNBuild = SeekNBuild(self.p2p, self.chain)
        
        self.genesisBinary = chainVars.genesisBinary
        
        self.intros = {}
        
        
    def run(self):
        if self.miner != None: self.miner.run()
        self.p2p.run()
        self.seekNBuild.shutdown()
        if self.miner != None: self.miner.shutdown()
        
        
    #=================
    # Decorators
    #=================
        
    def block(self, blockObject):
        self._Block = blockObject
        self.chain.setGenesis(self._Block().deserialize(BANT(self.genesisBinary)))
        return blockObject
        
        
    #==================
    # Cryptonet Handlers
    #==================
    
    def setHandlers(self):
        print('setHandlers')
        @self.p2p.on_connect
        def onConnectHandler(node):
            print('onConnectHandler')
            myIntro = Intro(topblock = self.chain.head.getHash())
            node.send('intro', ALL_BYTES(myIntro.serialize()))
            
            
        @self.p2p.handler('intro')
        def introHandler(node, payload):
            payload = ALL_BANT(payload)
            print('introHandler')
            try:
                theirIntro = Intro(payload)
            except ValidationError:
                node.misbehaving()
                return
            if config['networkdebug'] or True:
                debug('MSG intro : %s' % repr(theirIntro.getHash())[:8])
            if node in self.intros:
                return None
            self.intros[node] = theirIntro
            if not self.chain.hasBlock(theirIntro.topblock):
                self.seekNBuild.seekHash(theirIntro.topblock)
            

        @self.p2p.handler('blocks')
        def blocksHandler(node, payload):
            payload = ALL_BANT(payload)
            if config['networkdebug'] or True:
                debug('MSG blocks : %s' % repr(ghash(rlp.serialize(payload))[:8]))
            for pb in payload:
                try:
                    potentialBlock = self._Block(pb)
                    potentialBlock.assertInternalConsistency()
                except ValidationError:
                    node.misbehaving()
                    continue
                self.seekNBuild.addBlock(potentialBlock)
                self.seekNBuild.seekManyWithPriority(potentialBlock.relatedBlocks())
                        
            
        @self.p2p.handler('requestblocks')
        def requestblocksHandler(node, payload):
            payload = ALL_BANT(payload)
            if config['networkdebug'] or True:
                debug('MSG requestblocks : %s' % repr(ghash(RLP_SERIALIZE(payload))[:8]))
            # construct response
            ret = []
            for bh in payload:
                if self.chain.hasBlock(bh):
                    ret.append(self.chain.getBlock(bh).serialize())
            node.send('blocks', ALL_BYTES(ret))
            
        # done setting handlers
