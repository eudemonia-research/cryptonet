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
        self.invalid_block_hashes = set()
        self.block_hashes_with_priority = set()      # (sigma_diff, block_hash)

        self.genesis_block = None
        if genesis_block != None: self.set_genesis(genesis_block)

        self.seek_n_build = None

    def learn_of_seek_n_build(self, seek_n_build):
        self.seek_n_build = seek_n_build

    def restart_miner(self):
        if self.miner != None:
            self.miner.restart()

    def set_miner(self, miner):
        self.miner = miner

    def set_genesis(self, block):
        if self.genesis_block == None:
            block.assert_validity(self)

            self.genesis_block = block
            self.head = block

            self.add_block(block)
        else:
            raise ChainError('genesis block already known: %s' % self.genesis_block)

    def apply_block_to_head(self, new_head):
        ''' This applies the block to the head (which is checked).
        '''
        if self.initialized:
            assert new_head.parent_hash == self.head.get_hash()
        self.set_head(new_head)

    def set_head(self, new_head, no_reorg=False):
        if self.initialized and not no_reorg:
            self.head.reorganisation(new_head, self)
        self.head = new_head
        debug('chain: new head %d, hash: %064x' % (new_head.height, new_head.get_hash()))

    def add_block(self, block):
        ''' returns True on success
        '''
        if self.has_block(block):
            return

        self.db.set_entry(block.get_hash(), block)
        self.db.set_ancestors(block)
        self.blocks.add(block)
        self.block_hashes.add(block.get_hash())
        self.block_hashes_with_priority.add((block.priority, block.get_hash()))

        if block.better_than(self.head):
            self.apply_block_to_head(block)

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

    def find_lca(self, block_hash_a, block_hash_b):
        '''
        This finds the LCA of two blocks given their hashes.
        Currently walks through each blocks parents in turn until a match is found and returns that match.
        '''
        mutual_history = set()
        blocks = [self.get_block(block_hash_a), self.get_block(block_hash_b)]
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

    def construct_chain_path(self, start_block_hash, end_block_hash):
        ''' Returns a list of Blocks, in the range (start_block_hash, end_block_hash]
        '''
        reversed_path = []
        current_block_hash = end_block_hash
        while current_block_hash != start_block_hash:
            current_block = self.get_block(current_block_hash)
            reversed_path.append(current_block)
            current_block_hash = current_block.parent_hash
            if current_block_hash == 0:
                raise ChainError('No path possible. %064x is not an ancestor of %064x' % (start_block_hash, end_block_hash))
        return reversed_path[::-1]


    def apply_chain_path(self, path_to_apply):
        ''' path_to_apply is a list of blocks to apply sequentially.
        '''
        for block in path_to_apply:
            self.apply_block_to_head(block)

    def prune_to_height(self, height):
        ''' Set head to self.head's ancestor at specified height.
        '''
        self.assert_true(height <= self.head.height, 'Cannot prune forward.')
        self.assert_true(height >= 0, 'Cannot prune to a negative number.')
        current_block = self.head
        while current_block.height > height:
            current_block = self.get_block(current_block.parent_hash)
        self.set_head(current_block)


    def _construct_best_chain(self):
        ''' Find best block not in invalid_block_hashes.
        Run a reorg from head to that block.
        '''
        priority, block_hash = max(self.block_hashes_with_priority)
        debug('_construct_best_chain: priority, best_block: %d, %064x' % (priority, block_hash))
        best_chain_path = self.construct_chain_path(self.head.get_hash(), block_hash)
        self.apply_chain_path(best_chain_path)

    def _mark_invalid(self, invalid_block_hash):
        debug('Chain: Marking %064x as invalid' % invalid_block_hash)
        self.invalid_block_hashes.add(invalid_block_hash)
        if invalid_block_hash in self.block_hashes:
            invalid_block = self.get_block(invalid_block_hash)
            self.block_hashes.remove(invalid_block_hash)
            self.blocks.remove(invalid_block)
            self.block_hashes_with_priority.remove((invalid_block.priority, invalid_block_hash))

    def _recursively_mark_invalid(self, invalid_block_hash):
        children = self.get_children(invalid_block_hash)
        if children != None:
            for child in children[::-1]:
                self._recursively_mark_invalid(child)
        self._mark_invalid(invalid_block_hash)

    def recursively_mark_invalid(self, invalid_block_hash):
        ''' Mark invalid_block as invalid within the chain and recursively mark all children invalid.
        Wraps _recursively_mark_invalid() so _check_head_not_invalid() is only called once.
        '''
        self._recursively_mark_invalid(invalid_block_hash)
        self._make_head_not_invalid()
        self._construct_best_chain()

    def get_children(self, invalid_block_hash):
        ''' Find any children of block with hash invalid_block_hash.
        Returns a list.
        '''
        return self.db.get_children(invalid_block_hash)

    def _make_head_not_invalid(self):
        ''' If the head is invalid, set the head to head.parent until the head is valid.
        At which point call the reorganisation.
        '''
        old_head = self.head
        while self.head.get_hash() in self.invalid_block_hashes:
            self.set_head(self.get_block(self.head.parent_hash), no_reorg=True)
        old_head.reorganisation(self.head, self)

    def assert_true(self, condition, message):
        if not condition:
            raise ChainError(message)
