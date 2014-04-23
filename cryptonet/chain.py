import cryptonet
from cryptonet.debug import debug
from cryptonet.errors import ChainError
from cryptonet.utilities import global_hash


class Chain(object):
    ''' A blockchain.
    '''

    def __init__(self, chain_vars, genesis_block=None, db=None):
        """
        :param chain_vars: arbitrary ChainVars object
        :param genesis_block: serialized genesis block
        :param db: db if known (key-value store)
        :param cryptonet:
        """
        self.initialized = False
        self._Block = cryptonet.standard.Block
        self.head = None
        self.db = db
        self.miner = None
        self.blocks = set()
        self.block_hashes = set()

        self.genesis_block = None
        if genesis_block != None: self.set_genesis(genesis_block)

    def restart_miner(self):
        if self.miner != None:
            self.miner.restart()

    def set_miner(self, miner):
        self.miner = miner

    def hash(self, message):
        return global_hash(message)

    def set_genesis(self, block):
        if self.genesis_block == None:
            block.assert_validity(self)

            self.genesis_block = block
            self.head = block

            self.add_block(block)
        else:
            raise ChainError('genesis block already known: %s' % self.genesis_block)

    def set_new_head(self, new_head):
        if self.initialized:
            self.head.reorganisation(new_head, self)
        self.head = new_head
        debug('chain: new head %d, hash: %064x' % (new_head.height, new_head.get_hash()))


    # added sigmadiff stuff, need to test
    def add_block(self, block):
        ''' returns True on success
        '''
        if self.has_block(block):
            return

        self.db.set_entry(block.get_hash(), block)
        self.db.set_ancestors(block)
        self.blocks.add(block)
        self.block_hashes.add(block.get_hash())

        if block.better_than(self.head):
            self.set_new_head(block)

        if self.initialized == False:
            self.initialized = True

        debug('added block %d, hash: %064x' % (block.height, block.get_hash()))

        self.restart_miner()

        return True

    def get_block(self, block_hash):
        return self.db.get_entry(block_hash)

    def has_block(self, block):
        return block in self.blocks

    def has_block_hash(self, block_hash):
        return block_hash in self.block_hashes

    def get_height(self):
        return self.head.height

    def get_top_block(self):
        return self.head

    def get_ancestors(self, start):
        return self.db.get_ancestors(start)

    def load_chain(self):
        # TODO : load chainstate from database
        pass
        #self.db.get_successors(self.genesisHash)

    def learn_of_db(self, db):
        self.db = db
        self.load_chain()

    def find_lca(self, block_a, block_b):
        '''
        This finds the LCA of two blocks.
        Currently walks through each blocks parents in turn until a match is found and returns that match.
        '''
        mutual_history = set()
        blocks = [block_a, block_b]
        while True:
            if blocks[0] == blocks[1]:
                return blocks[0]
            if blocks[0].parent_hash == 0 and blocks[1].parent_hash == 0:
                raise ChainError('No LCA - different chains.')
            for i in range(len(blocks)):
                block_hash = blocks[i].get_hash()
                if block_hash in mutual_history:
                    # then this block is LCA
                    return blocks[i]
                mutual_history.add(block_hash)
                if blocks[i].parent_hash != 0:
                    blocks[i] = self.get_block(blocks[i].parent_hash)

    def construct_chain_path(self, start_block, end_block):
        pass

    def apply_chain_path(self, path_to_apply):
        ''' path_to_apply is a list of blocks to apply sequentially.
        '''
