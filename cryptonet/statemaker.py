from cryptonet.utilities import global_hash
from cryptonet.dapp import Dapp, TxPrism
from cryptonet.errors import ValidationError
from cryptonet.dapp import StateDelta
from cryptonet.chain import Chain
from cryptonet.debug import debug

''' statemaker.py
Contains 
    StateMaker: facilitates dapp functioning
    SuperState: holds all states
'''

ROOT_DAPP = b''

class _DappHolder(object):
    def __init__(self):
        self.dapps = {}

    def __getitem__(self, item):
        return self.dapps[item]

    def __setitem__(self, key, value):
        self.dapps[key] = value

    def __contains__(self, item):
        return item in self.dapps

    def on_block(self, block, chain):
        for d in self.dapps:
            self.dapps[d].on_block(block, chain)

    def prune_to_or_beyond(self, height):
        for d in self.dapps:
            self.dapps[d].prune_to_or_beyond(height)

    def checkpoint(self, hard_checkpoint=True):
        ''' Checkpoint all dapp states. '''
        for d in self.dapps:
            self.dapps[d].checkpoint(hard_checkpoint)

    def reset_to_last_hardened_checkpoint(self):
        ''' Apply to all dapp states. '''
        for d in self.dapps:
            self.dapps[d].reset_to_last_hardened_checkpoint()

    def make_last_checkpoint_hard(self):
        ''' Apply to all dapps. '''
        for d in self.dapps:
            self.dapps[d].make_last_checkpoint_hard()

    def start_trial(self, from_height):
        for d in self.dapps:
            self.dapps[d].start_trial(from_height)

    def end_trial(self, harden=False):
        for d in self.dapps:
            self.dapps[d].end_trial(harden)

class StateMaker(object):
    
    def __init__(self, chain):
        self.dapps = _DappHolder()
        self.chain = chain
        self.most_recent_block = None
        self.super_state = SuperState()

        self.register_dapp(TxPrism(ROOT_DAPP, self))
        
    def register_dapp(self, new_dapp):
        assert isinstance(new_dapp, Dapp)
        self.dapps[new_dapp.name] = new_dapp

    def find_prune_point(self, max_prune_height):
        return self.dapps[ROOT_DAPP].state.find_prune_point(max_prune_height)

    def prune_to_or_beyond(self, height):
        ''' Prune states to at least height. '''
        self.dapps.prune_to_or_beyond(height)

    def apply_chain_path(self, chain_path, hard_checkpoint=True):
        for block in chain_path:
            self.apply_block(block, hard_checkpoint)

    def apply_block(self, block, hard_checkpoint=True):
        block.set_state_maker(self)

        cur = self.super_state[b'']
        while cur.height > 0:
            debug('StateMaker.apply_block: all states', cur.key_value_store)
            print('> ', cur, cur.height)
            cur = cur.parent

        self.dapps.on_block(block, self.chain)
        self._add_super_txs(block.super_txs)
        block.assert_validity(self.chain)
        if block.height != 0:
            self.checkpoint(hard_checkpoint)
        
    def _add_super_txs(self, list_of_super_txs):
        ''' Process a list of transactions, typically passes each to the ROOT_DAPP in sequence.
        '''
        try:
            for super_tx in list_of_super_txs:
                for tx in super_tx.txs:
                    self._process_tx(tx)
        except AssertionError or ValidationError as e:
            self.reset_to_last_hardened_checkpoint()
            raise e
        return True
        
    def _process_tx(self, tx):
        ''' Pass tx to root dapp. Does not 'try,except' so shouldn't be used 
        outside of this class.
        The root dapp should act as a TxPrism and allocate transactions to other
        dapps as needed.
        '''
        self.dapps[ROOT_DAPP].on_transaction(tx, self.most_recent_block, self.chain)
            
    def checkpoint(self, hard_checkpoint=True):
        ''' Checkpoint all dapp states. '''
        self.dapps.checkpoint(hard_checkpoint)
    
    def reset_to_last_hardened_checkpoint(self):
        ''' Apply to all dapp states. '''
        self.dapps.reset_to_last_hardened_checkpoint()
            
    def make_last_checkpoint_hard(self):
        ''' Apply to all dapps. '''
        self.dapps.make_last_checkpoint_hard()

    def reorganisation(self, chain, from_block, around_block, to_block, is_test=False):
        ''' self.reorganisation() should be called on current head, where to_block is
        to become the new head of the chain.

        Steps:
        10. From around_block find the prune point
        15. Generate the chain_path_to_trial
        20. Conduct Trial
        30. Return result
        40. Mark trial head as invalid if the trial failed.
        '''
        assert isinstance(chain, Chain)
        debug('StateMaker.reorg: around_block.get_hash(): %064x' % around_block.get_hash())
        around_state_height = self.find_prune_point(around_block.height)
        debug('StateMaker.reorganisation: around_state_height: %d' % around_state_height)
        chain_path_to_trial = chain.construct_chain_path(around_block.get_hash(), to_block.get_hash())
        if is_test:
            success = self.trial_chain_path_non_permanent(around_state_height, chain_path_to_trial)
        else:
            success = self.trial_chain_path(around_state_height, chain_path_to_trial)
        if not success and not is_test:
            chain.recursively_mark_invalid(chain_path_to_trial[-1])
        return success

    def _trial_chain_path(self, around_state_height, chain_path_to_trial):
        success = True
        try:
            self.apply_chain_path(chain_path_to_trial, hard_checkpoint=False)
        except AssertionError or ValidationError as e:
            success = False
            debug(e)
            debug('StateMaker: trial failed, around: %d, proposed head: %064x' %
                  (around_state_height, chain_path_to_trial[-1].get_hash()))
        return success

    def trial_chain_path(self, around_state_height, chain_path_to_trial):
        ''' Warning: alters state permanently on success.
        '''
        self.start_trial(around_state_height)
        success = self._trial_chain_path(around_state_height, chain_path_to_trial)
        self.end_trial(harden=success)
        return success

    def trial_chain_path_non_permanent(self, around_state_height, chain_path_to_trial):
        self.start_trial(around_state_height)
        success = self._trial_chain_path(around_state_height, chain_path_to_trial)
        self.end_trial(harden=False)
        return success

    def start_trial(self, from_height):
        self.dapps.start_trial(from_height)

    def end_trial(self, harden=False):
        self.dapps.end_trial(harden=harden)
        if harden:
            debug('StateMaker.end_trial: Hardened checkpoints to state:')
            debug(self.dapps[ROOT_DAPP].state.key_value_store)


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
        debug('SuperState.register_dapp: name, state: %s, %s' % (name, state))
        self.state_dict[name] = state
        
    def get_hash(self):
        leaves = []
        names = self.state_dict.keys()
        # all names are bytes, need to investigate exactly how these are sorted.
        names.sort()
        for n in names:
            leaves.extend([global_hash(n), self.state_dict[n].get_hash()])
