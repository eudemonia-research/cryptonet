#!/usr/bin/env python3

import unittest
import threading
import time

import cryptonet
from examples.grachten import GrachtenBlock

class TestPeerFinding(unittest.TestCase):
    ''' Test messages
    To Test:
    blocks_handler:
        repeated sending of blocks should not break the connection - this should be in both directions
    '''

    def setUp(self):
        ''' Create (end-start) clients and have them connect to one other node (the preceding node in this case).

        '''
        self.start = 32555
        self.end = 32560
        chain_vars = []
        for i in range(self.start, self.end):
            chain_vars.append(cryptonet.datastructs.ChainVars())
            chain_vars[-1].mine = False
            chain_vars[-1].address = ('127.0.0.1', i)
            chain_vars[-1].seeds = [('127.0.0.1', i - 1)]
            chain_vars[-1].genesis_binary = b'\x01O\x01!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB!\x00\xd7gm\xa06{\xa2\xa6\xa3{\x0b\xd6\xb6\xc2\x80\xfc\x19\xca\xf5WD\x8am\xae\xe1+\xaf\xaa\x86\x9b\xfbB\t\x00\xabT\xa9\x8c\xdcgs\xf46\x01\x01\x01\x01\x00 \x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x02\x01\x00\x04SG\x9c\x93\x01\x00\x01\x00\x03\x01\x01\x00\x01\x01'

        self.networks = [cryptonet.Cryptonet(chain_vars=chain_vars[i]) for i in range(len(chain_vars))]

        for network in self.networks:
            network.block(GrachtenBlock)

        self.threads = [threading.Thread(target=n.run) for n in self.networks]
        for t in self.threads:
            t.start()


        time.sleep(2) # give everything time to warm up

    def test_peer_finding(self):
        print('starting!', self.networks)
        print('calling p2p.all_connected_peers()')
        print('peers 1/2', self.networks[0].p2p.all_connected_peers())
        print('p2p.num_connected_peers() hangs here')
        self.assertGreaterEqual(self.networks[0].p2p.num_connected_peers(), self.end-self.start)
        print('peers 2/2', self.networks[0].p2p.all_connected_peers())
        time.sleep(2)

        for n in self.networks:
            print(n.p2p.peers)
            n.p2p.shutdown()

    def tearDown(self):
        a = [n.p2p.shutdown() for n in self.networks]




if __name__ == '__main__':
    unittest.main()
