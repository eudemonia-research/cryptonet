'''Constants used in GDPHT'''

# incomming message maps

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
uncleList = ['hashtree', 'chaindata']
uncleMap = {
    'hashtree': 0,
    'chaindata': 1
    # uncles of uncles not considered
}
UM = uncleMap

chaindataList = [
    "version", 
    "height", 
    "target", 
    "sigmadiff", 
    "timestamp", 
    "votes", 
    "uncles", 
    "prevblock",
    ] # prev2, 4, 8, ... appended here
chaindataMap = dict([(title,n) for n,title in enumerate(chaindataList)])
CDM = chaindataMap

GENESISBLOCKHASH = b'\x00\xe7\xb4\xe1\x98\x36\xe0\x28\x2d\x40\x83\xad\xb9\xe1\xdb\x56\x30\x38\x95\xbf\x96\xec\xc4\xbf\x3a\xf8\x74\x45\xbb\xd0\xa8\x1f'

