# Cryptonet

A generic library to build blockchains with arbitrary properties.

Cryptonet is designed to facilitate extremely rapid development of cryptosystems. It is designed to be completely
modular, allowing almost everything to be modified in an isolated fashion.

There ~are~ will be many powerful built in modules that can enable even novice users to build structures such as
distributed markets.

## Conceptual Examples:

(These are a guide only of what the end result *should* look like (but it might not).)

### key value store

```
my_network = Cryptonet(ChainVars())

@my_network.dapp(b'KVS')
class KeyValueStore(Dapp):
    ''' A key value store could be used as a dns system. '''

    def on_transaction(self, tx, block, chain):
        key = sha3(tx.data[0])
        value = tx.data[1]
        if key not in self.state:
            self.state[key] = value

@my_network.dap(b'REGISTER')
class Register(Dapp):
    ''' This is a KVS with a fee that automatically funnels to one party. '''
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

* Test Std blocks, headers, etc
* Transaction P2P - handler
* Dapp.make_transaction()
* **min_coin alphanet** (currently working on)
* Marketcoin alphanet

## Done

* RPC mark 0
* Std blocks, headers, txs, etc
* ECDSA
* State (needs testing)
    * Dapp template
    * StateDeltas
    * SuperState
    * StateMaker
* Chain

## Dependancies

see setup.py.

## Examples

try:
```
Terminal 1:
python3 examples/grachten.py -mine
```
```
Terminal 2:
python3 examples/grachten.py -port 32556 -addnode 127.0.0.1:32555 -debug
```

args are currently stored in the example itself, so arguments won't work universally yet

## `min_coin`

You can run min_coin like so: `python3 examples/min_coin.py -add_nodes 198.199.102.43:32555 -mine -port 32555 -rpc_port 12344`

Then, in a new terminal:

```
> alias mc='rpc 127.0.0.1:12344'
> alias stdtx='./utils/stdtx'

> mc get_info
{
    "difficulty": 342601,
    "top_block hash": 300004629461987275343749802263029500466571070873970211316190874403973327,
    "top_block_height": 129
}

> mc get_ledger
{
    "55066263022277343669578718895168534326250603453777594175500187360389116729240": 6450000
}

> stdtx
usage: stdtx [-h] secret_exponent to_x amount [fee] [donation]
stdtx: error: the following arguments are required: secret_exponent, to_x, amount

> stdtx 0 1234567890987654321 1000000 200 300
01330131010101030f42400200c802012c23012101000000000000000000000000000000000000000000000000112210f4b16c1cb186012051bda76b4e2a057b9dde21fd861947efea533d56fb4ec1183ffbe65a635c74102100b048464711e62b2318c540db9ecc027e3615b13383476b8e4d65284718286e3a2079be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f8179820483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8

> mc push_tx 01330131010101030f42400200c802012c23012101000000000000000000000000000000000000000000000000112210f4b16c1cb186012051bda76b4e2a057b9dde21fd861947efea533d56fb4ec1183ffbe65a635c74102100b048464711e62b2318c540db9ecc027e3615b13383476b8e4d65284718286e3a2079be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f8179820483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
{
    "success": true,
    "relayed": true
}

( wait for a block )

> mc get_ledger
{
    "1234567890987654321": 1000000,
    "188899839028173": 300,
    "55066263022277343669578718895168534326250603453777594175500187360389116729240": 5499700
}

> mc get_info
{
    "top_block_height": 130,
    "difficulty": 342601,
    "top_block hash": 114877799261342757148804071220116137852294408957289398645657848834346206
}

```


## Standards

This are some of the possibilities for 'default' structures. Look in cryptonet.standards; it's pretty easy to read.

### Block

```
[
	header,
	uncles,
	[
	    stx1,
	    stx2,
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

### Super Tx

```
[
    [
        tx1,
        tx2,
        ...
    ],
    Signature
]
```

### Transaction

```
[
    to_dapp,
    amount,
    fee,
    donation,
    [
        bytes1,
        bytes2,
        ...
    ]
]
```

### Signature

```
[
    pubkey_x,
    pubkey_y,
    r,
    s
]
```
