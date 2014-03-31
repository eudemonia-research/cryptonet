#!/usr/bin/python

''' What will eventually become the pre-reference Gracht client.
Haskell client coming later. '''

from spore import Spore
from datastructs import *

# sketch of Gracht using Spore


intros = {}
introMap = {
	'version':0,
	'services':1,
	'timestamp':2,
	'addr_recv':3,
	'addr_from':4,
	'nonce':5,
	'user_agent':6,
	'topblock':7,
	'relay':8,
	'leaflets':9
}
IM = introMap
blockMap = {
	'hashtree': 0,
	'chaindata': 1,
	'uncles': 2
}
BM = blockMap
uncleMap = {
	'hashtree': 0,
	'chaindata': 1
	# uncles of uncles not considered
}
UM = uncleMap


def unrlp(t):pass
def rlp(t):pass


gracht = Spore()

gracht.set_recvieve_decode(RLP_DESERIALIZE)
gracht.set_send_encode(RLP_SERIALIZE)

@gracht.on_connect
@gracht.handler
def intro(node, payload):
	if node in intros:
		return None
	intros[node] = payload
	

@gracht.handler
def blocks(node, payload):
	debug('blocks : %s' % repr(payload))
	for block in payload:
		# [[hashtree],[header],[uncleslist]]
		ht = HashTree(block[BM['hashtree']])
		cd = ChainData(block[BM['chaindata']])
		uncles = Uncles(block[BM['uncles']])
		
		# if validBlock(ht, cd, uncles):
			# add block to whereever
			# validated on add
	hashtree = HashTree(json_loads(request.form['hashtree']))
	blockinfo = json_loads(request.form['blockinfo'])
	print '/newblock - hashtree: %s, blockinfo: %s' % (repr(hashtree.leaves), repr(blockinfo))
	added = chains[chain].addBlock(hashtree, blockinfo)
	if added == True:
		for n in knownNodes[chain]:
			print repr(n)
			n.sendMessage('/newblock', {'hashtree':hashtree.leaves(), 'blockinfo':blockinfo})
		return json.dumps({'error':''})
	return json.dumps({'error':added})
	
	
@gracht.handler
def requestblocks(node, payload):
	pass
	
	
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
	

@gracht.on_disconnect
@gracht.handler
def outro(node, payload):
	# TODO: after PoC
	pass
