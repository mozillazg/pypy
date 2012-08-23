#from _numpypy import *
#from .core import *

import sys
import math as _math
#sys.modules.setdefault('numpy', sys.modules['numpypy'])

import _numpypy
umath = _numpypy

import multiarray
sys.modules['numpy.core.multiarray'] = multiarray
sys.modules['numpy.core.umath'] = _numpypy

import numerictypes
sys.modules['numerictypes'] = numerictypes
sys.modules['numpy.core.numerictypes'] = numerictypes

import scalarmath
sys.modules['scalarmath'] = scalarmath
sys.modules['numpy.core.scalarmath'] = scalarmath

umath.ERR_IGNORE = 0
umath.ERR_WARN  = 1
umath.ERR_RAISE = 2
umath.ERR_CALL  = 3
umath.ERR_PRINT = 4
umath.ERR_LOG   = 5

umath.UFUNC_SHIFT_DIVIDEBYZERO = 0
umath.UFUNC_SHIFT_OVERFLOW   = 3
umath.UFUNC_SHIFT_UNDERFLOW  = 6
umath.UFUNC_SHIFT_INVALID    = 9

umath.UFUNC_BUFSIZE_DEFAULT = 8192
umath.ERR_DEFAULT2 = \
        (umath.ERR_WARN << umath.UFUNC_SHIFT_DIVIDEBYZERO) +  \
        (umath.ERR_WARN << umath.UFUNC_SHIFT_OVERFLOW) +      \
        (umath.ERR_WARN << umath.UFUNC_SHIFT_INVALID)

_errobj = [10000, 0, None]
def _seterrobj(*args):
    _errobj = args

umath.seterrobj = _seterrobj

umath.PINF = float('inf')
umath.NAN = float('nan')
umath.pi = _math.pi

del _math

def not_implemented_func(*args, **kwargs):
    raise NotImplementedError("implemented yet")

setattr(_numpypy, 'frompyfunc', not_implemented_func)
setattr(_numpypy, 'mod', not_implemented_func)
