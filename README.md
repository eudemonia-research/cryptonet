# Cryptonet

A generic library to build blockchains with arbitrary properties.

## Conceptual Examples:

(These are a guide only of what the end result *should* look like (but it might not).)

```
<network setup>

@my_network.dapp(b'KVS')
class KeyValueStore(Dapp):

    def on_block(self, block, chain):
        pass

    def on_transaction(self, tx, block, chain):
        key = sha3(tx.data[0])
        value = tx.data[1]
        if key not in self.state:
            self.state[key] = value

@my_network.dap(b'REGISTER')
class Register(Dapp):
    MY_OWNER = b'bobs_pubkey'
    BALANCE = 0

    def on_block(self, block, chain):
        self.make_transaction(MY_OWNER, self.state[BALANCE], 0, [])
        self.state[BALANCE] = 0

    def on_transaction(self, tx, block, chain):
        self.assert_true(tx.value >= 500)
        handle = tx.data[0]
        hashed_handle = sha3(handle)
        self.assert_true(hashed_handle not in self.state, 'Handle must not be taken.')
        self.state[hashed_handle] = tx.sender
        self.state[BALANCE] += tx.value

my_network.run()
```

Transactions sent to `KVS` are expected to have two arguments, a pre_key and a value. These could be a domain name and
IP address or a name and a phone number.

Transactions send to `REGISTER` are treated similarly, but there is a fee (which is 500 units) and they are stored
until the beginning of the next block when they are sent to MY_OWNER.

This comes pre-packaged with monetary units distributed as a mining reward.

## Things left to do:

* Standard blocks and headers
    * These are mostly done but largely untested.
* Transaction broadcasts & management (no mempool or P2P yet)
* ECDSA (txs validate signatures)
* RPC interface (started)
* Dapp.make_transaction()
* Marketcoin alphanet

## Done

* State (needs testing)
    * Dapp template
    * StateDeltas
    * SuperState
    * StateMaker
* Chain

## Dependancies

* python3
* Spore
* encodium
* pysha3 (maybe)

## Examples

try:
```
python3 examples/grachten.py -mine
python3 examples/grachten.py -addnode 127.0.0.1:32555
```

args are currently stored in the example itself, so arguments won't work universally yet

## Standards

This are some of the possibilities for 'default' structures.

### Block

```
[
	header,
	uncles,
	[
	    tx1,
	    tx2,
	    ...
	]
]
```

### Hash Tree

```
[
	item1, item2, ...
]

H: MerkleRoot( [i1, i2, i3, ...] )
```

### Headers

```
[
	version,
	nonce,
	height,
	timestamp,
	target,
	sigma_diff,
	state_mr,
	transaction_mr,
	uncles_mr,
	[
	    prevblock1,
        prevblock2,
        prevblock4,
        prevblock8,
        ...
	]
]
```

### Uncles List

```
[
	header,
	header,
	...
]
```