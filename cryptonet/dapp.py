''' dapp.py

Provides commonDapps. Eg: chainheaders
Provides resources to dapps. Eg: state
'''

class StateDelta(object):
    
    def __init__(self, parent=None, height=0):
        self.key_value_store = {}
        self.parent = parent
        self.height = height
        self.child = None
        
    def __getitem__(self, key):
        ''' return value if known else ask next statedelta '''
        if key in self.key_value_store:
            return self.key_value_store[key]
        if self.parent == None:
            raise KeyError('Unknown entry, not in State')
        return self.parent[key]
        
    def __setitem__(self, key, value):
        self.key_value_store[key] = value
        
    def ancestors(self):
        if self.parent == None: return [self]
        return [self] + self.parent.ancestors()
        
    def checkpoint(self):
        ''' Fork off from current StateDelta. 
        create a new state delta with new ancestors generated from [self] + self.ancestors (some may be merged).
        return that new StateDelta'''
        if self.child != None: raise Error('StateDelta: this SD already checkpointed')
        heights_to_keep = self.gen_checkpoint_heights(self.height + 1)
        for ancestor in self.ancestors():
            if ancestor.height not in heights_to_keep: ancestor.merge_with_child()
        new_state_delta = StateDelta(self, self.height + 1)
        self.child = new_state_delta
        return new_state_delta
            
    def merge_with_child(self):
        ''' triggers self.child.absorb(self) '''
        self.child.absorb(self)
        # destroy self by linking parents child to this child and vice versa
        # garbage collection should clean up?
        self.parent.child = self.child
        self.child.parent = self.parent
        
    def absorb(self, parent_state):
        ''' take state and underlay any entries in its key_value_store '''
        parent_keys = parent_state.key_value_store.keys()
        for k in parent_keys:
            if k in self.key_value_store: continue
            self.key_value_store[k] = parent_state.key_value_store[k]
         
    def gen_checkpoint_heights(self, height):
        ''' this generates the heights of StateDeltas that should be kept.
        If a height is not in this list it should be merged with its CHILD '''
        r, i = [], 0
        if height % 2 == 1: 
            r.append(height)
            height -= 1
        while height >= 0:
            r.append(height)
            if height % (2 ** (i+1)) != 0:
                height -= 2**i
                i += 1
            else: height -= 2**i
        return r
