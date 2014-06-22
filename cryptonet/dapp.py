from encodium import *

import cryptonet
from cryptonet.utilities import global_hash
from cryptonet.datastructs import MerkleLeavesToRoot
from cryptonet.debug import debug

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
        self.state_bank = {}
        self._set_state(StateDelta())


    def _synchronize_state(self):
        ''' Needed when self.state is set to a new object. '''
        self.super_state.register_dapp(self.name, self.state)

    def _set_state(self, new_state):
        self.state = new_state
        self._synchronize_state()

    def assert_true(self, condition, message):
        if not condition:
            raise ValidationError(message)

    def on_block(self, block, chain):
        ''' This is called when a new block arrives. Since many dapps won't
        use this event, raising NotImplemented here is unnecessary.
        '''
        #raise NotImplemented('on_block has not been implemented')
        pass

    def on_transaction(self, tx, block, chain):
        raise NotImplemented('on_transaction has not been implemented')

    def checkpoint(self, hard_checkpoint=True):
        ''' Checkpoint state. '''
        self._set_state(self.state.checkpoint(hard_checkpoint))

    def reset_to_last_checkpoint(self):
        ''' Apply to state. '''
        self._set_state(self.state.last_checkpoint())

    def make_last_checkpoint_hard(self):
        ''' Harden last checkpoint. '''
        self.state.parent.harden(self.state)

    def prune_to_or_beyond(self, height):
        ''' Set self.state to the best known state at a height equal to or less
        than the height provided.
        '''
        self._set_state(self.state.prune_to_or_beyond(height))

    def start_alt(self, state_tag, from_height):
        self.state_bank[b''] = self.state
        if state_tag not in self.state_bank:
            self.state_bank[state_tag] = self.state.child_at_or_before(from_height).checkpoint(hard_checkpoint=False)
        self._set_state(self.state_bank[state_tag])

    def end_alt(self, name, harden=False):
        assert name in self.state_bank
        if harden:
            self.state.harden(None)
        else:
            self.state_bank[name] = self.state
            self._set_state(self.state_bank[b''])

    def forget_alt(self, name):
        if name in self.state_bank:
            del self.state_bank[name]

    def get_height(self):
        return self.state.height


class StateDelta(object):

    # TODO : check if reorganisations from chain A to chain B and then to chain A+n will reuse states generated for chain A,
    # or will it regenerate all states from the point of the fork?

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

    def _make_key_valid(self, key):
        if not isinstance(key, int):
            key = int.from_bytes(key, 'big')
        if key < 0:
            raise KeyError('Negative entries not allowed')
        return key

    def __getitem__(self, key):
        ''' return value if known else ask next StateDelta '''
        key = self._make_key_valid(key)
        if key in self.deleted_keys:
            pass
        elif key in self.key_value_store:
            return self.key_value_store[key]
        elif self.parent != None:
            return self.parent[key]
        return 0


    def __setitem__(self, key, value):
        key = self._make_key_valid(key)
        if key in self.deleted_keys:
            self.deleted_keys.remove(key)
        self.my_hash = None
        self.key_value_store[key] = value

    def __delitem__(self, key):
        self.deleted_keys.add(key)
        if key in self.key_value_store:
            del self.key_value_store[key]

    def recursively_print_state(self):
        debug('StateDelta: %05d, %s', (self.height, self.key_value_store))
        if self.parent != None:
            self.parent.recursively_print_state()

    def all_keys(self):
        ''' Get keys from this k_v_store and parents, parents parents, etc.
        Returns a set. '''
        keys = set(self.key_value_store.keys())
        if self.parent != None:
            keys = keys.union(self.parent.all_keys())
        return keys - self.deleted_keys

    def complete_kvs(self):
        ''' Return flattened state as dict/k_v_store.
        '''
        return_key_value_store = {}
        all_keys = self.all_keys()
        for k in all_keys:
            return_key_value_store[k] = self[k]
        return return_key_value_store

    def get_hash(self):
        if self.my_hash == None:
            print(self.complete_kvs())
            keys = list(self.all_keys())
            debug('StateDelta: get_hash: keys', keys)
            # TODO: keys.sort() definition unknown ATM, needs to be specific so
            # identical states generate identical hashes (ints and bytes may be
            # being used as keys, not checked currently).
            keys.sort()
            leaves = []
            for k in keys:
                if isinstance(self[k], Field):
                    leaves.extend([global_hash(k), self[k].get_hash()])
                else:
                    leaves.extend([global_hash(k), global_hash(self[k])])
            merkle_tree = MerkleLeavesToRoot.make(leaves=leaves)
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
        new_state_delta = StateDelta(self, self.height + 1)
        if hard_checkpoint:
            self.harden(new_state_delta)
        return new_state_delta

    def harden(self, new_child, heights_to_keep=None):
        ''' Merge any state deltas that can be merged and set child. '''
        if heights_to_keep == None:
            heights_to_keep = self.gen_checkpoint_heights(self.height + 1)

        if new_child != None:
            self.child = new_child
            new_child.parent = self
        if self.height not in heights_to_keep:
            self.merge_with_child()
            self.parent.harden(self.child, heights_to_keep)
        elif self.parent != None:
            self.parent.harden(self, heights_to_keep)

    def last_checkpoint(self):
        ''' Return last checkpoint, which is self.parent. '''
        return self.parent

    def find_prune_point(self, max_prune_height):
        ''' This simply finds the best point to prune the chain taking into consideration the StateDeltas
        we have. Greatest height of checkpoints at or below max_prune_height.
        '''
        assert max_prune_height >= 0
        if self.height <= max_prune_height:
            debug('StateDelta: find_prune_point: returning %d' % self.height)
            return self.height
        return self.parent.find_prune_point(max_prune_height)

    def child_at_or_before(self, height):
        assert height >= 0
        if height >= self.height:
            return self
        return self.parent.child_at_or_before(height)

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
        # todo explanation
        r, i = [], 0
        if height % 2 == 1:
            r.append(height)
            height -= 1
        while height >= 0:
            r.append(height)
            if height % (2 ** (i + 1)) != 0:
                height -= 2 ** i
                i += 1
            else:
                height -= 2 ** i
        return r


#===============================================================================
# Common Dapps
#===============================================================================


class TxPrism(Dapp):

    # Used for coinbase transactions and anonymous submissions of block headers
    KNOWN_SECRET_EXPONENT = 0x1
    KNOWN_PUBKEY_X = 55066263022277343669578718895168534326250603453777594175500187360389116729240
    EUDEMONIA_PUBKEY_X = 0xABCDABCDABCD

    def on_block(self, block, chain):
        ''' Coinbase can be dealt with as follows:
         * grant pubkey with secret_exponent=0 some free coins and all tx fees.
         * Miner denies all received txs with that pubkey
         * Miner creates a signed tx emptying the 0-account balance - can distribute it single or multiple txs
         * This makes it flexible for pools, as the pay-everyone transaction can be shown to exist
        '''
        # TODO implement correctly and sensibly
        self.state[TxPrism.KNOWN_PUBKEY_X] += 50000  # or something
        # Future example schedule
        # Gold rush period: geometric series adjusted regularly (daily, probably)
        # Constant block production: some amount produced constantly

    def on_transaction(self, tx, block, chain):
        ''' Process a transaction.
        tx has following info (subject to change):
        tx.value, tx.fee, tx.data, tx.sender, tx.dapp

        tx.value >= 0 not >0 so 0 value txs (like notification of new foreign blocks) can be free
        '''
        self.assert_true(tx.value >= 0, 'tx.value must be greater than or equal to 0')
        self.assert_true(tx.fee >= 0, 'tx.fee must be greater than or equal to 0')
        self.assert_true(tx.donation >= 0, 'tx.donation must be greater than or equal to 0')
        debug('TxPrism.on_transaction', tx.sender)

        self.assert_true(self.state[tx.sender] >= tx.value + tx.fee + tx.donation, 'sender must have enough funds')

        self.state[tx.sender] -= tx.value + tx.fee + tx.donation
        self.state[TxPrism.KNOWN_PUBKEY_X] += tx.fee
        self.state[TxPrism.EUDEMONIA_PUBKEY_X] += tx.donation

        if tx.dapp == b'':
            self.assert_true(len(tx.data) == 1, 'Only one recipient allowed when sending to root dapp')
            self.assert_true(len(tx.data[0]) <= 33, 'recipient must be <= 32 bytes long (should be pubkey_x)')
            recipient = tx.data[0]
            self.state[recipient] += tx.value
        else:
            self.assert_true(tx.dapp in self.state_maker.dapps, 'dapp must be known')
            self.state[tx.dapp] += tx.value
            self.state_maker.dapps[tx.dapp].on_transaction(tx, block, chain)


class TxTracker(Dapp):
    ''' Special dapp to track transactions.
    Has the useful property that txs are now easy to prove they've
    happened without proving 'tx in block' and then 'block in main chain'.
    '''

    def on_transaction(self, super_tx, block, chain):
        self.assert_true(self.state[super_tx.get_hash()] == 0, 'SuperTx must not have been used previously')
        self.state[super_tx.get_hash()] = block.height

