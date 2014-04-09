class Database:
    ''' in-memory database for testing gracht '''
    def __init__(self):
        ''' everything stored in self.d.
        all keys should be hashes and all values should be lists '''
        self.d = {}

    def exists(self, key):
        return key in self.d
    
    def setEntry(self, key, value):
        self.d[key] = value
        
    def getEntry(self, key):
        return self.d[key]
        
    def rpush(self, key, val):
        if key not in self.d:
            self.d[key] = [val]
        else:
            self.d[key].append(val)
        
    def linkAnc(self, young, old, diff):
        self.rpush(old + diff, young)
        self.rpush(young - diff, old)
        
    def setAncestors(self, block):
        s = 0
        bh = block.getHash()
        cur = block.parenthash
        if cur == 0: return True # genesis block
        self.linkAnc(bh, cur, 2**s)
        while self.exists(cur - 2**s):
            cur = self.getEntry(cur - 2**s)[0] # going backwards will always have only one entry
            s += 1
            self.linkAnc(bh, cur, 2**s)
        return True
        
    def getAncestors(self, start):
        #print('\ngetAncestors : %s\n' % repr(self.d))
        ret = [start]
        s = 0
        cur = start
        if cur == 0: return ret # genesis block
        #print('\ngetAncestors subtest : %s\n' % repr(cur - 1))
        while self.exists(cur - 2**s):
            cur = self.getEntry(cur - 2**s)[0]
            s += 1
            ret.append(cur)
        return ret
