#!/usr/bin/python3

''' The purpose of this coin is to be the smallest cryptocurrency cryptonet can support.
It uses standard blocks and transactions, as well as TxPrism and TxTracker
'''

import argparse
from binascii import unhexlify

from cryptonet import Cryptonet
from cryptonet.datastructs import ChainVars
from cryptonet.debug import debug, enable_debug

import cryptonet.standard

GENESIS_HEX = '013a010101012501000453a6e5ca2001000000000000000000000000000000000000000000000000000000000000000201000100010001000301010001010101'

parser = argparse.ArgumentParser()
parser.add_argument('-mine', action='store_true', default=False, help='mine blocks, include flag to engage')
parser.add_argument('-add_nodes', nargs='*', default=[], type=str, help='node to connect to non-exclusively. Format xx.xx.xx.xx:yyyy')
parser.add_argument('-genesis', nargs=1, default=[GENESIS_HEX], type=str, help='bytes of genesis block if needed')
parser.add_argument('-network_debug', action='store_true', default=False)
parser.add_argument('-debug', action='store_true', default=False)
parser.add_argument('-port', nargs=1, default=[32555], type=int, help='port for node to bind to')
parser.add_argument('-rpc_port', nargs=1, default=[12345], type=int, help='port for rpc server to bind to')
args = parser.parse_args()

if args.debug:
    enable_debug()

seeds = [(h,int(p)) for h,p in [i.split(':') for i in args.add_nodes]]

print(args)

chain_vars = ChainVars(mine=args.mine, seeds=seeds, address=('0.0.0.0',args.port[0]), genesis_binary=unhexlify(args.genesis[0]))
min_coin = Cryptonet(chain_vars)

min_coin.block(cryptonet.standard.Block)
rpc = cryptonet.standard.RCPHandler(min_coin, args.rpc_port[0])

min_coin.run()