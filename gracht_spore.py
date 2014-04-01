#!/usr/bin/python3

''' What will eventually become the pre-reference Gracht client.
Haskell client coming later. '''

import time, argparse

from spore import Spore
from datastructs import *
from constants import *
from database import *


intros = {}

# GENESIS BLOCK
tree = HashTree([
	BANT("9ebac4128a78623a631834c395c1e044a5bb9bda46e49bbb7428e1a1ec3edc1a", True), 
	BANT("9ebac4128a78623a631834c395c1e044a5bb9bda46e49bbb7428e1a1ec3edc1a", True), 
	BANT("193f65c9e4e7b8b92d082784344fad9e732499bc1e7c63f89ae61832cccb7ccc", True), 
	BANT("193f65c9e4e7b8b92d082784344fad9e732499bc1e7c63f89ae61832cccceb9d", True)
	])
chaindata = Chaindata([
	BANT("00000001", True), 
	BANT("00000000", True), 
	BANT("ffffff02", True), 
	BANT("000000000000", True), 
	BANT("0000533a5be2", True), 
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
args = parser.parse_args()

config['port'] = args.port
seeds = []
if args.addnode != '':
	h,p = args.addnode.split(':')
	seeds.append((h,p))


db = Database()
gpdht = GPDHTChain(db=db, genesisBlock=genesisblock)


gracht = Spore(seeds=seeds, address=(config['host'], config['port']))

#gracht.set_recvieve_decode(RLP_DESERIALIZE)
#gracht.set_send_encode(RLP_SERIALIZE)

#@gracht.on_connect
@gracht.handler
def intro(node, payload):
	payload = RLP_DESERIALIZE(payload)
	if node in intros:
		return None
	intros[node] = payload
	

@gracht.handler
def blocks(node, payload):
	payload = RLP_DESERIALIZE(payload)
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
		#added =
	
	added = chains[chain].addBlock(hashtree, blockinfo)
	if added == True:
		for n in knownNodes[chain]:
			n.sendMessage('/newblock', {'hashtree':hashtree.leaves(), 'blockinfo':blockinfo})
		return json.dumps({'error':''})
	return json.dumps({'error':added})
	
	
@gracht.handler
def requestblocks(node, payload):
	payload = RLP_DESERIALIZE(payload)
	
	
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

try:
	while True:
		time.sleep(0.1)
except KeyboardInterrupt:
	gracht.stop()
