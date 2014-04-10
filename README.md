Cryptonet
=========

A generic library to build structures based on a blockchain with a P2P network.


## Dependancies

* python3
* Spore
* pysha3 (maybe)


## Standards

These will be reviewed before the beta. Currently designed for Gracht.

### Block

```
[
	hashtree,
	chaindata,
	uncleslist
]
```

### Hash Tree

```
[
	item1, item2, ...
]

H: MerkleRoot( [i1, i2, i3, ...] )
```

### Chain Data

```
[
	version,
	height,
	target,
	sigmadiff,
	timestamp,
	votes,
	uncles,
	prevblock1,
	prevblock2,
	prevblock4,
	prevblock8,
	...
]

H: h(RLP_SERIALIZE( chaindata ))
```

### Uncles List

```
[
	[hashtree, chaindata],
	[hashtree, chaindata],
	...
]

Remember each hashtree in the list above is a valid PoW in and of itself.

H: MerkleRoot( [ht1, ht2, ht3, ...] )
```

## Architecture

### SeekNBuild - find new blocks and ensure longest chain is being used.

R has five sets:

* future - set of hashes to seek out in the future (of potential blocks)
* present - set of hashes which are currently being sought (have been requested)
* past - set of hashes which have been found (full blocks then added to db)
* chain - set of hashes which have been added to the chain
* all - union of the above sets.

future, present, past, and chain are MUTUALY EXCLUSIVE => hashes should be in only one of them.

#### BlockSeeker

Takes random hashes from r_future and requests them from peers.
Adds hashes to r_present.

If there are no hashes in r_future and enough time has passed, re-request hashes in r_present from new peers.

loop

#### Blockhandler (EXTERNAL - P2P)

This is not part of the R class but interacts with it. This is the method called when a 'block' msg is recieved.

validate block as much as possible
remove block from r_pres and add to r_past
add block to db (but not chain)

#### ChainBuilder

This finds blocks that we know of but are as-yet unconnected to the main chain (which is really a tree). If the prevblock is in the chain then fully validate the block and add to the chain, re-organising if needed.

Remove block from r_past and add to r_chain

easy optimise: index r_past by height and only check <= topheight + 1

loop

