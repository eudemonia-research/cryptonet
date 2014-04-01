Gracht
======

Pre-reference implementation for GPDHT



## Standards

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
