#!/usr/bin/python

''' What will eventually become the pre-reference Gracht client.
Haskell client coming later. '''

import time

from spore import Spore
from datastructs import *
from constants import *
from database import *


intros = {}

db = Database()
gpdht = GPDHTChain(db=db)


gracht = Spore()

#gracht.set_recvieve_decode(RLP_DESERIALIZE)
#gracht.set_send_encode(RLP_SERIALIZE)

#@gracht.on_connect
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
	

#@gracht.on_disconnect
@gracht.handler
def outro(node, payload):
	# TODO: after PoC
	pass


gracht.start()

while True:
	
	time.sleep(0.1)
