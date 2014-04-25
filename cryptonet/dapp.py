from cryptonet.datastructs import MerkleLeavesToRoot
import cryptonet

''' dapp.py

Provides common dapps. Eg: TxPrism, ChainHeaders
Provides resources to dapps. Eg: StateDelta
'''

class Dapp(object):
    ''' The generic Dapp.
    All dapps should inherit from this class.
    self.on_transaction and self.on_block must be overloaded.
    '''
    
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
        
    def on_block(self, block, chain):
        ''' This is called when a new block arrives. Since many dapps won't
        use this event, raising NotImplemented here is unnecessary.
        '''
        #raise NotImplemented('on_block has not been implemented')
        pass
        
    def on_transaction(self, subtx, block, chain):
        raise NotImplemented('on_transaction has not been implemented')
        
    def checkpoint(self, hard_checkpoint=True):
        ''' Checkpoint state. '''
        self.set_state(self.state.checkpoint(hard_checkpoint))
    
    def reset_to_last_checkpoint(self):
        ''' Apply to state. '''
        self.set_state(self.state.last_checkpoint())
        
    def make_last_checkpoint_hard(self):
        ''' Harden last checkpoint. '''
        self.state.parent.harden(self.state)
        
    def prune_to_or_beyond(self, height):
        ''' Set self.state to the best known state at a height equal to or less
        than the height provided.
        '''
        self.set_state(self.state.prune_to_or_beyond(height))

class StateDelta(cryptonet.database.Database):
    
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
        ''' return value if known else ask next StateDelta '''
        if key < 0:
            raise KeyError('Negative entries not allowed')
        if key in self.deleted_keys:
            pass
        elif key in self.key_value_store:
            return self.key_value_store[key]
        elif self.parent != None:
            return self.parent[key]
        return 0
        
        
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
        return self.my_hash
        
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
            self.harden(new_state_delta)
        return new_state_delta
        
    def harden(self, new_child):
        ''' Merge any state deltas that can be merged and set child. '''
        heights_to_keep = self.gen_checkpoint_heights(self.height + 1)
        for ancestor in self.ancestors():
            if ancestor.height not in heights_to_keep: 
                ancestor.merge_with_child()
        self.child = new_child
        
    def last_checkpoint(self):
        ''' Return last checkpoint, which is self.parent. '''
        return self.parent

    def find_prune_point(self, max_prune_height):
        ''' This simply finds the best point to prune the chain taking into consideration the StateDeltas
        we have. Greatest height of checkpoints at or below max_prune_height.
        '''
        assert max_prune_height >= 0
        if self.height <= max_prune_height:
            return self.height
        return self.parent.find_prune_point(max_prune_height)
        
    def prune_to_or_beyond(self, height):
        ''' If this StateDelta is less than height, it is an acceptable prune,
        so return. If not, do what self.parent says.
        '''
        assert height >= 0
        if self.height <= height:
            self.child = None
            return self
        return self.parent.prune_to_or_beyond(height)
            
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
        

#===============================================================================
# Common Dapps
#===============================================================================

        
class TxPrism(Dapp):
    
    def on_block(self, tx, block, chain):
        # coinbase stuff?
        pass
        
    def on_transaction(self, tx, block, chain):
        ''' Process a transaction.
        tx has following info (subject to change):
        tx.value, tx.fee, tx.data, tx.sender, tx.dapp
        '''
        assert tx.value > 0
        assert tx.fee >= 0
        assert self.state[tx.sender] >= tx.value + tx.fee
        self.state[tx.sender] -= tx.value + tx.fee
        
        if tx.dapp == b'':
            assert len(tx.data) == 1
            recipient = tx.data[0]
            workingState[recipient] += tx.value
        else:
            assert tx.dapp in self.state_maker.dapps
            self.state[tx.dapp] += tx.value
            self.state_maker.dapps[tx.dapp].on_transaction(tx, block, chain)
            
            
            
