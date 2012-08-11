

typeinfo = {}
import _numpypy as ndarray
import _numpypy as array

from _numpypy import *
def bad_func(*args, **kwargs):
    raise ValueError('bad_func called')
def nop(*args, **kwargs):
    pass

def set_typeDict(*args, **kwargs):
    pass

datetime_data = bad_func
CLIP = 0
WRAP = 0
RAISE = 0
MAXDIMS = 0
ALLOW_THREADS = 0
BUFSIZE = 0

class nditer(object):
    '''
    doc_string will be set later
    '''
    def __init__(*args, **kwargs):
        raise ValueError('not implemented yet')

class nested_iters(object):
    def __init__(*args, **kwargs):
        raise ValueError('not implemented yet')

class broadcast(object):
    def __init__(*args, **kwargs):
        raise ValueError('not implemented yet')

def copyto(dst, src, casting='same_kind', where=None, preservena=False):
    raise ValueError('not implemented yet')

def count_nonzero(a):
    try:
        if not hasattr(a,'flat'):
            a = ndarray(a)
        return sum(a.flat != 0)
    except TypeError:
        if isinstance(a, (tuple, list)):
            return len(a)
    return 1

def empty_like(a, dtype=None, order='K', subok=True):
    if not hasattr(a,'dtype'):
        a = ndarray(a)
    if dtype is None:
        dtype = a.dtype
    if order != 'K' and order != 'C':
        raise ValueError('not implemented yet')
    #return zeros(a.shape, dtype=dtype, order=order, subok=subok)
    return zeros(a.shape, dtype=dtype)

def fromiter(iterable, dtype, count=-1):
    if count > 0:
        retVal = ndarray(count, dtype=dtype)
    else:
        retVal = ndarray(1, dtype=dtype)
    for i,value in enumerate(iterable):
        if i>=count and count>0:
            break
        if i>= retVal.size:
            tmp = ndarray(retVal.size*2, dtype = dtype)
            tmp[:i] = retVal[:i]
            retVal = tmp
        retVal[i] = value
    return retVal[:i+1]
