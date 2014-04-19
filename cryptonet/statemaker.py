from cryptonet import global_hash

''' statemaker.py
Contains StateMaker class def and SuperState class def
'''

class StateMaker(object):
    
    def __init__(self):
        self.dapps = {}
        
    def register_dapp(self, new_dapp):
        self.dapps[new_dapp.name] = new_dapp
        

class SuperState(object):
    ''' SuperState()
    Holds other states in name:state dictionary (each pair belonging to a dapp).
    Merkle tree arranged like: [H(name1), MR(state1), H(name2), MR(state2), ...]
    where H(x) hashes x and MR(y) returns the merkle root of y.
    self.get_hash() returns the merkle root of the above tree.
    '''
    
    def __init__(self):
        self.state_dict = {}
        
    def register_dapp(self, name, state):
        self.state_dict[name] = state
        
    def get_hash(self):
        leaves = []
        names = self.state_dict.keys()
        # all names are bytes, need to investigate exactly how these are sorted.
        names.sort()
        for n in names:
            leaves.extend([global_hash(n), self.state_dict[n].get_hash()])
