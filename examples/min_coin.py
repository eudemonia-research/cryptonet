#!/usr/bin/python3

''' The purpose of this coin is to be the smallest cryptocurrency cryptonet can support.
It uses standard blocks and transactions, as well as TxPrism and TxTracker
'''

from cryptonet import Cryptonet
from cryptonet.datastructs import ChainVars
import cryptonet.standard

chain_vars = ChainVars()
chain_vars.mine = True
min_coin = Cryptonet(chain_vars)

min_coin.block(cryptonet.standard.Block)
rpc = cryptonet.standard.RCPHandler(min_coin, 12346)

min_coin.run()