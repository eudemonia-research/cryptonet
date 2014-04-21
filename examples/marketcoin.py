#!/usr/bin/env python3

from cryptonet import Cryptonet
import cryptonet.template


marketcoin = Cryptonet()


## Must be accessible to on_block:
            
#@marketcoin.dapp(b'BTC_CH')
class BitcoinChainheaders(cryptonet.template.Dapp):
    ''' Chainheaders will track all provided chain headers and keep track of the
    longest chain.
    Initial state should have ~genesis block hash~ some recent checkpoint for Bitcoin network.
    '''

    def on_block(self, block, chain):
        pass

    def on_transaction(self, tx, block, chain):
        # should accept a list of block headers and validate to store the longest chain
        assert len(tx.data) > 0
        for rawHeader in tx.data:
            header = cryptonet.Chainheaders.Bitcoin(workingState, rawHeader) # pass in working state so things like previous_block and sigmadiff can be set
            header.assert_validity(workingState)
            BitcoinChainheaders.add_header_to_state(workingState, header)
            
        return workingState
            
    @staticmethod
    def add_header_to_state(workingState, header):
        bh = header.get_hash()
        if workingState[bh] != 0:
            raise ValidationError('BitcoinChainheaders: blockheader already added')
        workingState[bh] = header
        
        tophash = workingState[b'TOPHASH']
        topheader = workingState[tophash]



@marketcoin.dapp(b'BTC_SPV')
class BitcoinSPV(cryptonet.template.Dapp):
    ''' SPV and MerkleTree verification.
    SPV takes a block hash, 2 transaction hashes, and a merkle branch.
    The merkle branch should prove those two transaction hashes were included
    in the merkle tree of the header to which the block_hash belongs. Although
    this can be done with partial branches (as in the first two hashes aren't tx
    hashes, but are half way through the merkle tree) there is little benefit.
        1. Verify merkle branch is correct. Should result in MR from block
        2. Verify MR is in header 
        3. Set txhash XOR block_hash to 1'''
    
    @staticmethod
    def on_block(workingState, block, chain):
        return workingState
        
    @staticmethod
    def on_transaction(workingState, tx, chain):
        ''' Prove some BTC transaction was in some merkle tree via tx hash.
        If tx ABCD was in block 1234 then 1234 XOR ABCD will be set to 1. '''
        return workingState
        
        
        
@marketcoin.dapp(b'BTC_MARKET')
class BitcoinMarket(cryptonet.template.Dapp):
    ''' Market has a few functions:
        0. execute occasionally
        1. accept bids for MKC
        2. accept asks for BTC
        3. cancel order
        4. prove order fulfilled (show BTC payment)
        5. redeem pledge (if order went unfulfilled)
    First data entry decides which to do (except execution, that's automagic).
    Inputs:
    1. min_return (in MKC), max_spend (in BTC)     # output to account that provided pledge
    2. min_return (in BTC), fulfillment_requirement (output script) # max spend is tx.value
    3. order-hash or something # tx.sender is verification of ownership
    4. ordermatch id, rawtx (from BTC network), block_hash (which includes tx)
    5. 
    '''
    
    @staticmethod
    def on_block(workingState, block, chain):
        ''' Test for market execution condition and if so execute. '''
        return workingState
        
    @staticmethod
    def on_transaction(workingState, tx, chain):
        ''' Depending on tx either insert, cancel, fulfill, or _ specified order '''
        return workingState

