#!/usr/bin/env python3

''' What will eventually become the pre-reference Gracht client.
Haskell client coming later. '''

import time, argparse

from spore import Spore
from datastructs import *
from constants import *
from database import *
from seeknbuild import *
from miner import Miner

intros = {}

# GENESIS BLOCK
tree = HashTree([
	BANT("4da5bb26a234e081daa99197f4f546616a1a56ec10f55211e9cbca3db12c4468", True), 
	BANT("4da5bb26a234e081daa99197f4f546616a1a56ec10f55211e9cbca3db12c4468", True), 
	BANT("193f65c9e4e7b8b92d082784344fad9e732499bc1e7c63f89ae61832cccb7ccc", True), 
	BANT("193f65c9e4e7b8b92d082784344fad9e732499bc1e7c63f89ae61832cccb8ef2", True)
	])
chaindata = Chaindata([
	BANT("00000001", True), 
	BANT("00000000", True), 
	BANT("ffffff02", True), 
	BANT("010000", True), 
	BANT("0000533cf190", True), 
	BANT("00000000", True), 
	BANT("0000000000000000000000000000000000000000000000000000000000000000", True), 
	BANT("0000000000000000000000000000000000000000000000000000000000000000", True)
	])
genesisblock = (tree, chaindata)




config = {
	'host': '0.0.0.0',
	'port': 32555
}

parser = argparse.ArgumentParser()
parser.add_argument('-port', nargs=1, default=32555, type=int, help='port for node to bind to')
parser.add_argument('-addnode', nargs=1, default='', type=str, help='node to connect to non-exclusively. Format xx.xx.xx.xx:yyyy')
parser.add_argument('-genesis', nargs=1, default=BANT(), type=BANT, help='genesis block in hex')
parser.add_argument('-mine', action='store_true')
args = parser.parse_args()

config['port'] = args.port
seeds = []
if args.addnode != '':
	h,p = args.addnode.split(':')
	seeds.append((h,p))


db = Database()
gpdht = GPDHTChain(db=db, genesisBlock=genesisblock)

gracht = Spore(seeds=seeds, address=(config['host'], config['port']))

seeknbuild = SeekNBuild(gracht, gpdht)

if args.mine:
	miner = Miner(gpdht)

#gracht.set_recvieve_decode(RLP_DESERIALIZE)
#gracht.set_send_encode(RLP_SERIALIZE)

#@gracht.on_connect
@gracht.handler
def intro(node, payload):
	payload = ALLBANT(payload)
	if node in intros:
		return None
	intros[node] = payload
	

@gracht.handler
def blocks(node, payload):
	payload = ALLBANT(payload)
	debug('blocks : %s' % repr(payload))
	for block in payload:
		# [[hashtree],[header],[uncleslist]]
		ht = HashTree(block[BM['hashtree']])
		cd = ChainData(block[BM['chaindata']])
		uncles = Uncles(block[BM['uncles']])
		
		if not validPoW(ht, cd): 
			#node.misbehaving()
			continue
		
		# add to pre-validated blocks
		h = ht.getHash()
		if h not in seeknbuild.all:
			with seeknbuild.past_lock:
				seeknbuild.all.add(h)
				seeknbuild.past.add(h)
				seeknbuild.addToPastByHeight(h, cd.height)
				seeknbuild.pastFullBlocks[h] = [ht, cd, uncles] # should use blockmap for this, maybe block obj
				# TODO : add prevblocks to future,all
				
	
	
@gracht.handler
def requestblocks(node, payload):
	payload = ALLBANT(payload)
	
	
@gracht.handler
def entries(node, payload):
	# TODO: after PoC
	pass


@gracht.handler
def requestentries(node, payload):
	# TODO: after PoC
	pass
	
	
@gracht.handler
def proof(node, payload):
	# TODO: after PoC
	pass
	
	
@gracht.handler
def requestproof(node, payload):
	# TODO: after PoC
	pass
	
	
@gracht.handler
def alert(node, payload):
	# TODO: after PoC
	pass
	

@gracht.handler
def unknown(node, payload):
	# TODO: after PoC
	pass
	

#@gracht.on_disconnect
@gracht.handler
def outro(node, payload):
	# TODO: after PoC
	pass


gracht.start()

if args.mine:
	miner.start()

try:
	while True:
		time.sleep(0.1)
except KeyboardInterrupt:
	gracht.stop()
	seeknbuild.stop()
	if args.mine:
		miner.stop()
