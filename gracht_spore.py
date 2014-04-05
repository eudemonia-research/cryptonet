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
if isinstance(args.port, list): config['port'] = args.port[0]
seeds = []
if isinstance(args.addnode, list) and args.addnode[0] != '':
    h,p = args.addnode[0].split(':')
    seeds.append((h,p))


db = Database()
gpdht = GPDHTChain(db=db, genesisBlock=genesisblock)

gracht = Spore(seeds=seeds, address=(config['host'], config['port']))

seeknbuild = SeekNBuild(gracht, gpdht)

if args.mine:
    miner = Miner(gpdht, seeknbuild)

#gracht.set_recvieve_decode(RLP_DESERIALIZE)
#gracht.set_send_encode(RLP_SERIALIZE)

@gracht.on_connect
def onConnect(node):
    myIntro = [b'' for _ in range(len(IM))]
    myIntro[IM['topblock']] = bytes(gpdht.head.getHash())
    node.send('intro', ALL_BYTES(myIntro))
    
    
@gracht.handler('intro')
def intro(node, payload):
    payload = ALL_BANT(payload)
    if node in intros:
        return None
    intros[node] = payload
    topblock = payload[IM['topblock']]
    if not gpdht.hasBlock(topblock):
        seeknbuild.addBlocksToSeek([payload[IM['topblock']]])
    

@gracht.handler('blocks')
def blocks(node, payload):
    payload = ALL_BANT(payload)
    debug('MSG blocks : %s' % repr(ghash(RLP_SERIALIZE(payload))[:8]))
    for block in payload:
        # [[hashtree],[header],[uncleslist]]
        ht = HashTree(block[BM['hashtree']])
        cd = Chaindata(block[BM['chaindata']])
        uncles = Uncles(block[BM['uncles']])
        
        if not validPoW(ht, cd): 
            #node.misbehaving()
            debug('MSG blocks handler : PoW failed for %s' % repr(ht.getHash()))
            continue
        seeknbuild.addBlock(ht, cd)
        # TODO : add prevblocks to future,all
        seeknbuild.addBlocksToSeek(cd.prevblocks)
                
    
@gracht.handler('requestblocks')
def requestblocks(node, payload):
    payload = ALL_BANT(payload)
    # construct response
    ret = []
    for bh in payload:
        if gpdht.hasBlock(bh):
            leaves = db.getEntry(bh)
            cdraw = db.getEntry(leaves[1])
            uncles = []
            ret.append([leaves, cdraw, uncles])
    node.send('blocks', ALL_BYTES(ret))
    
    
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


if args.mine:
    miner.start()

gracht.run()

seeknbuild.stop()
if args.mine:
    miner.stop()
