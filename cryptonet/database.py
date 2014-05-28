from cryptonet.debug import debug


class Database:
    ''' An in-memory key value store for testing cryptonet '''

    def __init__(self):
        ''' Everything is stored in self.key_value_store.
        Typically keys will be hashes and values will be lists. '''
        self.key_value_store = {}

    def key_exists(self, key):
        return key in self.key_value_store

    def set_entry(self, key, value):
        self.key_value_store[key] = value

    def get_entry(self, key):
        return self.key_value_store[key]

    def rpush(self, key, val):
        if key not in self.key_value_store:
            self.key_value_store[key] = [val]
        else:
            self.key_value_store[key].append(val)

    def link_ancestor(self, young, old, diff):
        self.rpush(old + diff, young)
        self.rpush(young - diff, old)

    def set_ancestors(self, block):
        s = 0
        bh = block.get_hash()
        cur = block.parent_hash
        if cur == 0: return True  # genesis block
        self.link_ancestor(bh, cur, 2 ** s)
        while self.key_exists(cur - 2 ** s):
            cur = self.get_entry(cur - 2 ** s)[0]  # going backwards will always have only one entry
            s += 1
            self.link_ancestor(bh, cur, 2 ** s)
        return True

    def get_ancestors(self, start):
        #print('\ngetAncestors : %s\n' % repr(self.d))
        ret = [start]
        index = 0
        cur = start
        if cur == 0:
            return ret  # genesis block
        #print('\ngetAncestors subtest : %s\n' % repr(cur - 1))
        while self.key_exists(cur - 2 ** index):
            cur = self.get_entry(cur - 2 ** index)[0]
            index += 1
            ret.append(cur)
        return ret

    def get_children(self, block_hash):
        ''' block_hash + delta gives all blocks at (height of block_hash) + delta
        '''
        if (block_hash + 1) in self.key_value_store:
            return self.get_entry(block_hash + 1)
