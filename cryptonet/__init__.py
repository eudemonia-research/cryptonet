from spore import Spore
#from . import defaultStructures
from cryptonet.seeknbuild import SeekNBuild
from cryptonet.gpdht import *
from cryptonet.database import Database
from cryptonet.errors import *
from cryptonet.datastructs import *
from cryptonet.miner import Miner
from cryptonet.debug import *

config = {'networkdebug':True}

class Cryptonet(object):
    def __init__(self, chainVars):
        self._Block = None
        
        self.p2p = Spore(seeds=chainVars.seeds, address=chainVars.address)
        self.setHandlers()
        debug('cryptonet init, peers: ', self.p2p.peers)
        
        self.db = Database()
        self.chain = Chain(chainVars, db=self.db)
        self.seekNBuild = SeekNBuild(self.p2p, self.chain)
        self.miner = None
        if chainVars.mine:
            self.miner = Miner(self.chain, self.seekNBuild)
        
        self.mineGenesis = False
        if chainVars.genesisBinary == None: self.mineGenesis = True
        else: self.genesisBinary = chainVars.genesisBinary
        
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
        if self.mineGenesis:
            pass
        else:
            self.chain.setGenesis(self._Block().make(self.genesisBinary))
        return blockObject
        
        
    #==================
    # Cryptonet Handlers
    #==================
    
    def setHandlers(self):
        debug('setHandlers')
        @self.p2p.on_connect
        def onConnectHandler(node):
            debug('onConnectHandler')
            myIntro = Intro.make(topblock=bytes(self.chain.head.getHash()))
            node.send('intro', myIntro.serialize())
            
            
        @self.p2p.handler('intro')
        def introHandler(node, payload):
            debug('introHandler')
            try:
                theirIntro = Intro.make(payload)
            except ValidationError:
                node.misbehaving()
                return
            if config['networkdebug'] or True:
                debug('MSG intro : %s' % repr(theirIntro.getHash()[:8]))
            if node in self.intros:
                return None
            self.intros[node] = theirIntro
            if not self.chain.hasBlock(theirIntro.topblock):
                debug('introhand', theirIntro.topblock)
                self.seekNBuild.seekHash(theirIntro.topblock)
            

        @self.p2p.handler('blocks')
        def blocksHandler(node, payload):
            blockList = BlockList.make(payload)
            if config['networkdebug'] or True:
                debug('MSG blocks : %s' % repr(blockList.getHash()[:8]))
            for blockser in blockList.blocks:
                try:
                    potentialBlock = self._Block().make(blockser)
                    potentialBlock.assertInternalConsistency()
                except ValidationError as e:
                    debug('blocksHandler error', e)
                    #node.misbehaving()
                    continue
                self.seekNBuild.addBlock(potentialBlock)
                self.seekNBuild.seekManyWithPriority(potentialBlock.relatedBlocks())
                        
            
        @self.p2p.handler('requestblocks')
        def requestblocksHandler(node, payload):
            hashList = HashList.make(payload)
            if config['networkdebug'] or True:
                debug('MSG requestblocks : %s' % repr(ghash(payload)[:8]))
            ret = BlockList()
            for bh in hashList:
                if self.chain.hasBlockhash(bh):
                    ret.append(self.chain.getBlock(bh).serialize())
            node.send('blocks', ret.serialize())
            
        # done setting handlers
