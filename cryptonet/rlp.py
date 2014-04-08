import gpdht
BANT = gpdht.BANT

i2b = lambda x : x.to_bytes((x.bit_length() // 8) + 1, 'big')

def wrap_deserialize(rlpIn):
    if rlpIn.raw()[0] >= 0xc0:
        if rlpIn.raw()[0] > 0xf7:
            sublenlen = rlpIn.raw()[0] - 0xf7
            sublen = rlpIn[1:sublenlen+1].int()
            msg = rlpIn[sublenlen+1:sublenlen+sublen+1]
            rem = rlpIn[sublenlen+sublen+1:]
        
        else:
            sublen = rlpIn.raw()[0] - 0xc0
            msg = rlpIn[1:sublen+1]
            rem = rlpIn[sublen+1:]
            
        o = []
        while len(msg) > 0:
            t, msg = wrap_deserialize(msg)
            o.append(t)
        return o, rem
    
    elif rlpIn.raw()[0] > 0xb7:
        subsublen = rlpIn.raw()[0] - 0xb7
        sublen = rlpIn[1:subsublen+1].int()
        msg = rlpIn[subsublen+1:subsublen+sublen+1]
        rem = rlpIn[subsublen+sublen+1:]
        return msg, rem
        
    elif rlpIn.raw()[0] >= 0x80:
        sublen = rlpIn.raw()[0] - 0x80
        msg = rlpIn[1:sublen+1]
        rem = rlpIn[sublen+1:]
        return msg, rem
    
    else:
        return rlpIn[0], rlpIn[1:]
        
def deserialize(rlpIn):
    if not isinstance(rlpIn, BANT): raise ValueError("RLP_DESERIALIZE requires a BANT as input")
    if len(rlpIn) == 0: return rlpIn
    ret, rem = wrap_deserialize(rlpIn)
    if rem != BANT(''): raise ValueError("RLP_DESERIALIZE: Fail, remainder present")
    return ret
    
def encode_len(b, islist = False):
        if len(b) == 1 and not islist and b < 0x80:
            return bytearray([])
        elif len(b) < 56:
            if not islist: return bytearray([0x80+len(b)])
            return bytearray([0xc0+len(b)]) 
        else:
            if not islist: return bytearray([0xb7+len(i2b(len(b)))]) + bytearray(i2b(len(b)))
            return bytearray([0xf7+len(i2b(len(b)))]) + bytearray(i2b(len(b)))
    
def serialize(blistIn):
    rt = bytearray(b'')
    
    if isinstance(blistIn, list):
        for b in blistIn:
            rt.extend( serialize(b).raw() )
        
        ret = encode_len(rt, True)
        ret.extend(rt)
    else:
        try:
            rt.extend(encode_len(blistIn) + blistIn.raw())
            ret = rt
        except:
            raise ValueError('input is not a BANT or a list')
    
    return BANT(ret)
