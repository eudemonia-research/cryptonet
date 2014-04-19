from cryptonet.datastructs import MerkleLeavesToRoot

''' dapp.py

Provides commonDapps. Eg: chainheaders
Provides resources to dapps. Eg: statedeltas
'''

class Dapp(object):
    
    def __init__(self, name, state_maker):
        assert isinstance(name, bytes)
        self.name = name
        self.state_maker = state_maker
        self.state_maker.register_dapp(self)
        self.super_state = state_maker.super_state
        self.set_state(StateDelta())
        
    def synchronize_state(self):
        ''' Needed when self.state is set to a new object. '''
        self.super_state.register_dapp(self.name, self.state)
        
    def set_state(self, new_state):
        self.state = new_state
        self.synchronize_state()
        
    @staticmethod
    def on_block(working_state, block, chain):
        raise NotImplemented('on_block has not been implemented')
        
    @staticmethod
    def on_transaction(working_state, block, chain):
        raise NotImplemented('on_transaction has not been implemented')

class StateDelta(object):
    
    def __init__(self, parent=None, height=0):
        self.key_value_store = {}
        self.parent = parent
        self.height = height
        self.child = None
        self.my_hash = None
        self.deleted_keys = set()
        
    def __contains__(self, key):
        if key in self.deleted_keys:
            return False
        if key in self.key_value_store:
            return True
        if self.parent == None:
            return False
        return key in self.parent
        
    def __getitem__(self, key):
        ''' return value if known else ask next statedelta '''
        if key in self.deleted_keys:
            pass
        elif key in self.key_value_store:
            return self.key_value_store[key]
        elif self.parent != None:
            return self.parent[key]
        raise KeyError('Unknown key, %x' % key)
        
        
    def __setitem__(self, key, value):
        if key in self.deleted_keys:
            self.deleted_keys.remove(key)
        self.my_hash = None
        self.key_value_store[key] = value
        
    def __delitem__(self, key):
        self.deleted_keys.add(key)
        if key in self.key_value_store:
            del self.key_value_store[key]
        
    def all_keys(self):
        ''' Get keys from this k_v_store and parents, parents parents, etc.
        Returns a set. '''
        keys = set(self.key_value_store.keys())
        if self.parent != None:
            keys.add(self.parent.all_keys())
        return keys
        
    def get_hash(self):
        if self.my_hash == None:
            keys = list(self.all_keys())
            # TODO: keys.sort() definition unknown ATM, needs to be specific so
            # identical states generate identical hashes (ints and bytes may be
            # being used as keys, not checked currently).
            keys.sort()
            leaves = []
            for k in keys:
                leaves.extend([k, self.key_value_store[k]])
            merkle_tree = MerkleLeavesToRoot(leaves)
            self.my_hash = merkle_tree.get_hash()
        
    def ancestors(self):
        if self.parent == None: 
            return [self]
        return [self] + self.parent.ancestors()
        
    def checkpoint(self, hard_checkpoint=True):
        ''' Fork off from current StateDelta if hard_checkpoint == True.
        Some ancestors may be merged.
        Return a new StateDelta.
        '''
        if self.child != None: 
            raise ValueError('StateDelta: this SD already checkpointed')
        new_state_delta = StateDelta(self, self.height + 1)
        if hard_checkpoint:
            heights_to_keep = self.gen_checkpoint_heights(self.height + 1)
            for ancestor in self.ancestors():
                if ancestor.height not in heights_to_keep: 
                    ancestor.merge_with_child()
            self.child = new_state_delta
        return new_state_delta
            
    def merge_with_child(self):
        ''' Triggers self.child.absorb(self); links self.child and self.parent. '''
        self.child.absorb(self)
        # destroy self by linking parents child to this child and vice versa
        # garbage collection should clean up?
        self.parent.child = self.child
        self.child.parent = self.parent
        
    def absorb(self, parent_state):
        ''' Takes a state and underlay any entries in self.key_value_store '''
        parent_keys = parent_state.key_value_store.keys()
        for k in parent_keys:
            if k in self.key_value_store: 
                continue
            self.key_value_store[k] = parent_state.key_value_store[k]
         
    def gen_checkpoint_heights(self, height):
        ''' Generates the heights of StateDeltas that should be kept.
        If a height is not in this list it should be merged with self.child.
        '''
        r, i = [], 0
        if height % 2 == 1: 
            r.append(height)
            height -= 1
        while height >= 0:
            r.append(height)
            if height % (2 ** (i+1)) != 0:
                height -= 2**i
                i += 1
            else: 
                height -= 2**i
        return r
