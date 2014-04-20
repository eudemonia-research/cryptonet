from cryptonet import global_hash
from cryptonet.dapp import Dapp, TxPrism
from cryptonet.errors import ValidationError

''' statemaker.py
Contains 
    StateMaker: facilitates dapp functioning
    SuperState: holds all states
'''

class StateMaker(object):
    
    def __init__(self):
        self.dapps = {}
        self.most_recent_block = None
        
    def register_dapp(self, new_dapp):
        self.dapps[new_dapp.name] = new_dapp
        
    def prune_to_or_beyond(self, height):
        ''' Prune states to at least height. '''
        for d in self.dapps:
            self.dapps[d].prune_to_or_beyond(height)
        
    def add_super_txs(self, list_of_super_txs):
        ''' Process a list of transactions, passing each to the respective dapp.
        '''
        try:
            for super_tx in list_of_super_txs:
                for tx in super_tx.txs:
                    self._process_tx(tx)
        except AssertionError:
            self.reset_to_last_checkpoint()
            return False
        return True
        
    def _process_tx(self, tx):
        ''' Pass tx to dapp. Does not 'try,except' so shouldn't be used outside
        of this class.
        '''
        self.dapps[tx.dapp].on_transaction(tx, self.most_recent_block, self.chain)
            
    def checkpoint(self, hard_checkpoint=True):
        ''' Checkpoint all dapp states. '''
        for d in self.dapps:
            self.dapps[d].checkpoint(hard_checkpoint)
    
    def reset_to_last_checkpoint(self):
        ''' Apply to all dapp states. '''
        for d in self.dapps:
            self.dapps[d].reset_to_last_checkpoint()
            
    def make_last_checkpoint_hard(self):
        ''' Apply to all dapps. '''
        for d in self.dapps:
            self.dapps[d].make_last_checkpoint_hard()
            
        

class SuperState(object):
    ''' SuperState()
    Holds other states in name:state dictionary (each pair belonging to a dapp).
    Merkle tree arranged like: [H(name1), MR(state1), H(name2), MR(state2), ...]
    where H(x) hashes x and MR(y) returns the merkle root of y.
    self.get_hash() returns the merkle root of the above tree.
    '''
    
    def __init__(self):
        self.state_dict = {}
        
    def __getitem__(self, key):
        return self.state_dict[key]
        
    def register_dapp(self, name, state):
        self.state_dict[name] = state
        
    def get_hash(self):
        leaves = []
        names = self.state_dict.keys()
        # all names are bytes, need to investigate exactly how these are sorted.
        names.sort()
        for n in names:
            leaves.extend([global_hash(n), self.state_dict[n].get_hash()])
