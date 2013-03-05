import core
from core import *
import lib
from lib import *

from __builtin__ import bool, int, long, float, complex, object, unicode, str
from core import abs, max, min

__all__ = []
__all__ += core.__all__
__all__ += lib.__all__

import sys
#sys.modules.setdefault('numpy', sys.modules['numpypy'])

from _numpypy import multiarray
sys.modules.setdefault('multiarray', multiarray)

def set_typeDict(*args, **kwargs):
    pass


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

multiarray.set_typeDict = set_typeDict
multiarray.CLIP = 0
multiarray.WRAP = 0
multiarray.RAISE = 0
multiarray.MAXDIMS = 0
multiarray.ALLOW_THREADS = 0
multiarray.BUFSIZE = 0
multiarray.nditer = nditer
multiarray.nested_iters = nested_iters
multiarray.broadcast = broadcast

from _numpypy import umath
sys.modules.setdefault('umath', umath)
from _numpypy import numerictypes
sys.modules.setdefault('numerictypes', numerictypes)

numerictypes.sctypeDict = None
