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

global_hash = ghash

class Cryptonet(object):
    def __init__(self, chainVars):
        self._Block = None
        
        self.p2p = Spore(seeds=chainVars.seeds, address=chainVars.address)
        self.setHandlers()
        debug('cryptonet init, peers: ', self.p2p.peers)
        
        self.db = Database()
        self.chain = Chain(chainVars, db=self.db, cryptonet=self)
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
            myIntro = Intro.make(topblock=self.chain.head.get_hash())
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
                debug('MSG intro : %064x' % theirIntro.get_hash())
            if node in self.intros:
                return None
            self.intros[node] = theirIntro
            if not self.chain.hasBlock(theirIntro.topblock):
                debug('introhand', theirIntro.topblock)
                self.seekNBuild.seekHash(theirIntro.topblock)
            

        @self.p2p.handler('blocks')
        def blocksHandler(node, payload):
            blocklist = BytesList.make(payload)
            if config['networkdebug'] or True:
                debug('MSG blocks : %064x' % blocklist.get_hash())
            for serializedBlock in blocklist:
                try:
                    potentialBlock = self._Block().make(serializedBlock)
                    potentialBlock.assertInternalConsistency()
                except ValidationError as e:
                    debug('blocksHandler error', e)
                    #node.misbehaving()
                    continue
                self.seekNBuild.addBlock(potentialBlock)
                self.seekNBuild.seekManyWithPriority(potentialBlock.relatedBlocks())
                        
            
        @self.p2p.handler('requestblocks')
        def requestblocksHandler(node, payload):
            requests = HashList.make(payload)
            if config['networkdebug'] or True:
                debug('MSG requestblocks : %064x' % requests.get_hash())
            ret = BytesList.make()
            for bh in requests:
                if self.chain.hasBlockhash(bh):
                    ret.append(self.chain.getBlock(bh).serialize())
            if ret.len() > 0:
                node.send('blocks', ret.serialize())
            
        # done setting handlers
