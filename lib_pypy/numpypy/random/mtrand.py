import random
from numpypy import zeros
def random_sample(length=0):
    if length == 0:
        return random.random()
    ret = zeros((length,))
    for x in xrange(length):
        ret[x] = random.random()
    return ret

def randn(length=0):
    if length == 0:
        return random.gauss(0., 1.)
    ret = zeros((length,))
    for x in xrange(length):
        ret[x] = random.gauss(0., 1.)
    return ret
