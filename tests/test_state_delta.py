#!/usr/bin/env python3

import unittest

from cryptonet.dapp import StateDelta

class TestStateDelta(unittest.TestCase):
    ''' Test StateDelta class
    To Test:
    * getitem with multiple state deltas
    * checkpointing
    * merge with child
    * absorb
    * gen_checkpoint_heights
    * after 100 checkpoints everything is as expected
    '''
    
    # TODO : Test `del state_delta[item]`
    
    def setUp(self):
        self.genesis_state_delta = StateDelta()
        self.genesis_state_delta[0] = 0
        self.current_state = self.genesis_state_delta
        
    def test_del_item(self):
        cur = self.current_state
        cur[0] = 1
        self.assertTrue(0 in cur)
        del cur[0]
        self.assertTrue(0 not in cur)
        cur[0] = 1
        cur = cur.checkpoint()
        self.assertTrue(0 in cur)
        cur = cur.checkpoint()
        self.assertTrue(0 in cur)
        del cur[0]
        self.assertTrue(0 not in cur)

    def test_easy_checkpoint(self):
        cur = self.current_state
        for i in range(1,11): 
            cur = cur.checkpoint()
            cur[i] = i
        self.assertEqual(cur.height, 10)
        self.assertEqual(len(cur.ancestors()), 6)
        
        # ensure easy merges / absorbs work
        expected_k_vs = [
            {10:10},
            {9:9},
            {8:8,7:7},
            {6:6,5:5},
            {4:4,3:3,2:2,1:1},
            {0:0}
        ]
        for i in range(len(expected_k_vs)):
            self.assertEqual(cur.ancestors()[i].key_value_store, expected_k_vs[i])
        self.assertEqual(cur[0], 0)
        with self.assertRaises(KeyError):
            a = cur[-1]
            
    def test_merge_precedence(self):
        ''' deliberately overwrite old key and ensure that even after that SD
        has been merged the value remains the same '''
        cur = StateDelta()
        cur = cur.checkpoint()
        cur[1] = [1]
        for i in range(1,11): 
            if i == 5:
                cur[1] = 5
            cur = cur.checkpoint()
        self.assertEqual(cur[1], 5)
        
    
    def test_checkpoint_heights(self):
        expected_results = [
            (1024, [1024, 1023, 1022, 1020, 1016, 1008, 992, 960, 896, 768, 512, 0]),
            (1023, [1023, 1022, 1021, 1020, 1018, 1016, 1012, 1008, 1000, 992, 976, 960, 928, 896, 832, 768, 640, 512, 256, 0]),
            (999, [999, 998, 997, 996, 994, 992, 988, 984, 976, 960, 928, 896, 832, 768, 640, 512, 256, 0]),
            (999007, [999007, 999006, 999005, 999004, 999002, 999000, 998996, 998992, 998984, 998976, 998960, 998944, 998912, 998848, 998784, 998656, 998400, 997888, 997376, 996352, 995328, 993280, 991232, 987136, 983040, 974848, 966656, 950272, 917504, 851968, 786432, 655360, 524288, 262144, 0]),
        ]
        
        # check generation is correct
        for h, r in expected_results:
            self.assertEqual(self.current_state.gen_checkpoint_heights(h), r)
        
        # test property that a reorg of size n requires no more than 2n 
        # recalculations of state
        for h, r in expected_results:
            # don't test first or last - trivial cases anyway
            for i in range(1,len(r)-1): 
                # choose reorg_point to be worst possibilities
                reorg_point = r[i]-1
                # ensure that recalcs of state in a reorg is strictly less than 
                # twice the length of the reorg
                self.assertTrue(h - r[i-1] < (h - reorg_point) * 2)



if __name__ == '__main__':
    unittest.main()
