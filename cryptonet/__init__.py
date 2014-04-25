from spore import Spore
#from . import defaultStructures
from cryptonet.seeknbuild import SeekNBuild
from cryptonet.chain import Chain
from cryptonet.utilities import global_hash
from cryptonet.database import Database
from cryptonet.errors import ValidationError
from cryptonet.datastructs import *
from cryptonet.miner import Miner
from cryptonet.debug import debug
import cryptonet.standard

config = {'network_debug':True}

# TODO: STATE
# TODO: ECDSA
# TODO: Alerts

class Cryptonet(object):
    def __init__(self, chain_vars):
        self._Block = None
        
        self.p2p = Spore(seeds=chain_vars.seeds, address=chain_vars.address)
        self.set_handlers()
        debug('cryptonet init, peers: ', self.p2p.peers)
        
        self.db = Database()
        self.chain = Chain(chain_vars, db=self.db)
        self.seek_n_build = SeekNBuild(self.p2p, self.chain)
        self.miner = None
        if chain_vars.mine:
            self.miner = Miner(self.chain, self.seek_n_build)
        
        self.mine_genesis = False
        if chain_vars.genesis_binary == None: self.mine_genesis = True
        else: self.genesis_binary = chain_vars.genesis_binary
        
        self.intros = {}
        
    def run(self):

        if self.miner != None: self.miner.run()
        self.p2p.run()
        self.seek_n_build.shutdown()
        if self.miner != None: self.miner.shutdown()

    def shutdown(self):
        self.p2p.shutdown()
        
    #=================
    # Decorators
    #=================
        
    def block(self, block_object):
        self._Block = block_object
        if self.mine_genesis:
            pass
        else:
            self.chain.set_genesis(self._Block().make(self.genesis_binary))
        return block_object
        
        
    #==================
    # Cryptonet Handlers
    #==================
    
    def set_handlers(self):
        debug('set_handlers')
        @self.p2p.on_connect
        def on_connect_handler(node):
            debug('on_connect_handler')
            my_intro = Intro.make(top_block=self.chain.head.get_hash())
            node.send('intro', my_intro.serialize())
            
            
        @self.p2p.handler('intro')
        def intro_handler(node, payload):
            debug('intro_handler')
            try:
                their_intro = Intro.make(payload)
            except ValidationError:
                node.misbehaving()
                return
            if config['network_debug'] or True:
                debug('MSG intro : %064x' % their_intro.get_hash())
            if node in self.intros:
                return None
            self.intros[node] = their_intro
            if not self.chain.has_block(their_intro.top_block):
                debug('introhand', their_intro.top_block)
                self.seek_n_build.seek_hash_now(their_intro.top_block)
            

        @self.p2p.handler('blocks')
        def blocks_handler(node, payload):
            block_list = BytesList.make(payload)
            if config['network_debug'] or True:
                debug('MSG blocks : %064x' % block_list.get_hash())
            for serialized_block in block_list:
                try:
                    potential_block = self._Block().make(serialized_block)
                    potential_block.assert_internal_consistency()
                except ValidationError as e:
                    debug('blocks_handler: serialized_block:', serialized_block)
                    debug('blocks_handler error', e)
                    #node.misbehaving()
                    continue
                self.seek_n_build.add_block(potential_block)
                self.seek_n_build.seek_many_with_priority(potential_block.related_blocks())
                        
            
        @self.p2p.handler('request_blocks')
        def request_blocks_handler(node, payload):
            requests = HashList.make(payload)
            if config['network_debug'] or True:
                debug('MSG request_blocks : %064x' % requests.get_hash())
            ret = BytesList.make()
            for bh in requests:
                if self.chain.has_block_hash(bh):
                    ret.append(self.chain.get_block(bh).serialize())
            if ret.len() > 0:
                node.send('blocks', ret.serialize())
            
        # done setting handlers
