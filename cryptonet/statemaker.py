from cryptonet.utilities import global_hash
from cryptonet.dapp import Dapp, TxPrism, TxTracker
from cryptonet.errors import ValidationError
from cryptonet.dapp import StateDelta
from cryptonet.debug import debug
from cryptonet.datastructs import MerkleLeavesToRoot
from cryptonet.constants import ROOT_DAPP, TX_TRACKER

''' statemaker.py
Contains 
    StateMaker: facilitates dapp functioning
    SuperState: holds all states
'''

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

    def get_height(self):
        return self.dapps[ROOT_DAPP].get_height()

    def prune_to_or_beyond(self, height):
        for d in self.dapps:
            self.dapps[d].prune_to_or_beyond(height)

    def checkpoint(self, hard_checkpoint=True):
        ''' Checkpoint all dapp states. '''
        for d in self.dapps:
            self.dapps[d].checkpoint(hard_checkpoint)

    def reset_to_last_hardened_checkpoint(self):
        ''' Apply to all dapp states. '''
        debug('RESET TO LAST CHECKPOINT')
        for d in self.dapps:
            self.dapps[d].reset_to_last_checkpoint()

    def make_last_checkpoint_hard(self):
        ''' Apply to all dapps. '''
        for d in self.dapps:
            self.dapps[d].make_last_checkpoint_hard()

    # todo: refactor to checkout_alt
    def start_alt(self, state_tag, from_height):
        for d in self.dapps:
            self.dapps[d].start_alt(state_tag, from_height)

    # todo: refactor to commit_alt
    def end_alt(self, state_tag, harden=False):
        for d in self.dapps:
            self.dapps[d].end_alt(state_tag, harden)

    def forget_alt(self, state_tag):
        for d in self.dapps:
            self.dapps[d].forget_alt(state_tag)

    def generate_super_state(self):
        debug('Generating super state')
        super_state = SuperState()
        for d in self.dapps:
            dapp = self.dapps[d]
            super_state.register_dapp(dapp.name, dapp.state)
        return super_state


class StateMaker(object):
    def __init__(self, chain, is_future=False):
        self.dapps = _DappHolder()
        self.chain = chain
        self.most_recent_block = None
        self.super_state = SuperState()
        # System Dapps
        self.register_dapp(TxPrism(ROOT_DAPP, self))
        self.register_dapp(TxTracker(TX_TRACKER, self))
        self.is_future = is_future
        self.future_state_maker = None
        self.future_block = None
        self._Block = chain._Block

    def register_dapp(self, new_dapp):
        assert isinstance(new_dapp, Dapp)
        self.dapps[new_dapp.name] = new_dapp

    def get_height(self):
        return self.dapps.get_height()

    def find_prune_point(self, max_prune_height):
        return self.dapps[ROOT_DAPP].state.find_prune_point(max_prune_height)

    def prune_to_or_beyond(self, height):
        ''' Prune states to at least height. '''
        self.dapps.prune_to_or_beyond(height)

    def apply_chain_path(self, chain_path, hard_checkpoint=True):
        for block in chain_path:
            self.apply_block(block, hard_checkpoint)

    def apply_block(self, block, hard_checkpoint=True):
        debug('StateMaker.apply_block, heights:', block.height, self.dapps[ROOT_DAPP].state.height)
        assert block.height == self.dapps[ROOT_DAPP].state.height
        self._block_events(block)
        block.assert_validity(self.chain)
        if block.height != 0:
            self.checkpoint(hard_checkpoint)

    def _block_events(self, block):
        ''' What is done every time a block is received - operates directly on current state.
        '''
        block._set_state_maker(self)
        self.dapps.on_block(block, self.chain)
        self._add_super_txs(block.super_txs)
        block.update_roots()

    def apply_super_tx_to_future(self, super_tx):
        ''' This applies a transaction to future_block.
         The state will be updated and a new block available when pushed to the miner.
         - This is equivalent to adding the tx to the mem-pool
         '''
        with self.future_state():
            self._add_super_txs([super_tx])
            self.future_block.super_txs.append(super_tx)
            self.future_block.update_roots()

    def _add_super_txs(self, list_of_super_txs):
        ''' Process a list of transactions, typically passes each to the ROOT_DAPP in sequence.
        '''
        try:
            for super_tx in list_of_super_txs:
                self.dapps[TX_TRACKER].on_transaction(super_tx, self.most_recent_block, self.chain)
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
        assert not self.is_future
        debug('StateMaker.reorg: around_block.get_hash(): %064x' % around_block.get_hash())
        around_state_height = self.find_prune_point(around_block.height)
        debug('StateMaker.reorganisation: around_state_height: %d' % around_state_height)
        chain_path_to_trial = chain.construct_chain_path(around_block.get_hash(), to_block.get_hash())
        if is_test:
            success = self.trial_chain_path_non_permanent(around_state_height, chain_path_to_trial)
        else:
            success = self.trial_chain_path(around_state_height, chain_path_to_trial)
        if not success and not is_test:
            chain.recursively_mark_invalid(chain_path_to_trial[-1].get_hash())
        if not is_test and success:
            self._refresh_future_block(to_block)
            self.most_recent_block = to_block
        return success

    def _refresh_future_block(self, new_head):
        ''' Should be called on .reorganisation() to ensure unconfirmed transactions are remembered (if still legit).
        Will create an unvalidated block to store keep track of future state and the rest of it. Everything within
        future_block will be temporary and discarded and recalculated on the arrival of every new block.
        '''
        self.forget_future_state()
        self.future_block = new_head.get_pre_candidate(self.chain)
        with self.future_state():
            # calc tx_root and state_root
            # do stuff like update state here with any as yet excluded txs
            # and only add txs not included in last block, etc
            self._block_events(self.future_block)
            # This will hold a copy of the future states of dapps; forgotten on next refresh.
            self.future_super_state = self.dapps.generate_super_state()


    def _trial_chain_path(self, around_state_height, chain_path_to_trial):
        success = True
        try:
            self.apply_chain_path(chain_path_to_trial, hard_checkpoint=False)
        except (ValidationError) as e:
            success = False
            debug(e)
            debug('StateMaker: trial failed, around: %d, proposed head: %064x' %
                  (around_state_height, chain_path_to_trial[-1].get_hash()))
        return success

    def trial_chain_path(self, around_state_height, chain_path_to_trial):
        ''' Warning: alters state permanently on success.
        Test the provided chain path and if successful alter the state.
        '''
        with self.trial_state(around_state_height) as temporary_state:
            success = self._trial_chain_path(around_state_height, chain_path_to_trial)
            if success:
                temporary_state.make_permanent()
        return success

    def trial_chain_path_non_permanent(self, around_state_height, chain_path_to_trial):
        with self.trial_state(around_state_height) as temporary_state:
            success = self._trial_chain_path(around_state_height, chain_path_to_trial)
        return success

    def _alt_state_gateway(self, state_tag, from_height, amnesia=False):
        '''returns an instance of AltStateGateway class.
        When an AltStateGateway is entered the state is a non-permanent trail state.
        Modifications may be made freely.
        Upon exiting the AltStateGateway the value of .harden will determine if the
        state is made permanent or not.

        Use:
        with self._alt_state_gateway(b'my_state_tag', 1000):
            my_state[b'hi there'] = 1
        '''

        class AltStateGateway(object):
            '''Changes the state to a temp state identified by a tag.
            Should be used with the `with` statement.

            amnesia=False: if amnesia is set to True the temp state identified by state_tag will be forgotten.
            EG: the future state will not be amnesiac, but trialing a chain-path is.
            '''

            def __init__(self, state_maker, state_tag, from_height, amnesia=False):
                self.state_maker = state_maker
                self.from_height = from_height
                self.state_tag = state_tag
                self.amnesia = amnesia
                self.harden = False

            def __enter__(self):
                self.state_maker.dapps.start_alt(self.state_tag, self.from_height)
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.state_maker.dapps.end_alt(self.state_tag, harden=self.harden)
                if self.amnesia:
                    self.state_maker.dapps.forget_alt(self.state_tag)

            def make_permanent(self):
                self.harden = True

        return AltStateGateway(self, state_tag, from_height, amnesia=amnesia)

    def future_state(self):
        return self._alt_state_gateway(b'future', self.get_height())

    def forget_future_state(self):
        self.dapps.forget_alt(b'future')

    def trial_state(self, from_height=None):
        if from_height == None:
            from_height = self.get_height()
        return self._alt_state_gateway(b'trial', from_height, amnesia=True)


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
        names = list(self.state_dict.keys())
        # all names are bytes, need to investigate exactly how these are sorted.
        names.sort()
        for n in names:
            leaves.extend([global_hash(n), self.state_dict[n].get_hash()])
        merkle_root = MerkleLeavesToRoot.make(leaves=leaves)
        debug('SuperState: root: ', merkle_root.get_hash(), [self.state_dict[n].complete_kvs() for n in names])
        return merkle_root.get_hash()

