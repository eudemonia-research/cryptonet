Cryptonet
=========

A generic library to build blockchains with arbitrary properties.


## Dependancies

* python3
* Spore
* encodium
* pysha3 (maybe)

## Examples

try:

```
python3 examples/minblock.py
python3 examples/grachten.py -mine
```

## Standards

This are some of the possibilities for 'default' structures.

### Block

```
[
	header,
	uncles,
	transactions
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
	height,
	target,
	sigma_diff,
	timestamp,
	uncles_mr,
	state_mr,
	transaction_mr,
	prevblock1,
	prevblock2,
	prevblock4,
	prevblock8,
	...
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

## Architecture

### SeekNBuild - find new blocks and ensure longest chain is being used.

SeekNBuild uses a few queues:

* future - set of hashes to seek out in the future (of potential blocks)
* present - set of hashes which are currently being sought (have been requested)
* past - set of hashes which have been found (full blocks then added to db)
* all - union of the above sets.

Hashes move between the three queues to track where they are.

The seeker broadcasts request_blocks messages.

The builder takes blocks, adds them to the chain, then broadcasts.

