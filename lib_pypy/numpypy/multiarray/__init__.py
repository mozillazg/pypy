

typeinfo = {}
import _numpypy as ndarray
import _numpypy as array

from _numpypy import *
from _numpypy import dtype, empty
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
    if i<count:
        raise ValueError('iterator too short')
    return retVal[:i+1]

def fromfile(_file, dtype=float, count=-1, sep=''):
    raise ValueError('not implemented yet')

def frombuffer(buffer, dtype=float, count=-1, offset=0):
    raise ValueError('not implemented yet')

def newbuffer(size):
    return bytearray(size)

def getbuffer(a, *args):
    if not hasattr(a,'size'):
        a = ndarray(a)
    offset = 0
    size = a.size
    if len(args)>0:
        offset = args[0]
    if len(args)>1:
        size = args[1]
    raise ValueError('not implemented yet')

def int_asbuffer(*args, **kwargs):
    raise ValueError('not implemented yet')

def _fastCopyAndTranspose(*args, **kwargs):
    raise ValueError('not implemented yet')

def set_numeric_ops(**kwargw):
    raise ValueError('not implemented yet')

def can_cast(fromtype, totype, casting = 'safe'):
    if not isinstance(fromtype, dtype):
        raise ValueError('improper call to can_cast')
    if not isinstance(totype, dtype):
        raise ValueError('improper call to can_cast')
    if casting not in ('no', 'equiv', 'safe', 'same_kind', 'unsafe'):
        raise ValueError('improper call to can_cast')
    raise ValueError('not implemented yet')

def promote_types(type1, type2):
    if not isinstance(type1, dtype):
        raise ValueError('improper call to can_cast')
    if not isinstance(type2, dtype):
        raise ValueError('improper call to can_cast')
    raise ValueError('not implemented yet')

def min_scalar_type(a):
    raise ValueError('not implemented yet')

def result_type(*args):
    raise ValueError('not implemented yet')

def lexsort(keys, axis=-1):
    raise ValueError('not implemented yet')

def compare_chararrays(*args, **kwargs):
    raise ValueError('not implemented yet')

def putmask(a, mask, values):
    raise ValueError('not implemented yet')

def einsum(subscripts, *operands, **kwargs):
    #kwargs is out=None, dtype=None, order='K', casting='safe'
    raise ValueError('not implemented yet')

def inner(a,b):
    raise ValueError('not implemented yet')

def format_longfloat(*args, **kwargs):
    raise ValueError('not implemented yet')

def datetime_as_string(*args, **kwargs):
    raise ValueError('not implemented yet')

def busday_offset(dates, offsets, roll='raise', weekmask='1111100', holidays=None, busdaycal=None, out=None):
    raise ValueError('not implemented yet')

def busday_count(begindates, enddates, weekmask='1111100', holidays=[], busdaycal=None, out=None):
    raise ValueError('not implemented yet')

def is_busday(dates, weekmask='1111100', holidays=None, busdaycal=None, out=None):
    raise ValueError('not implemented yet')

def busdaycalendar(weekmask='1111100', holidays=None):
    raise ValueError('not implemented yet')

def _vec_string(*args, **kwargs):
    raise ValueError('not implemented yet')


