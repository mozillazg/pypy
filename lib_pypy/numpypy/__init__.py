#from _numpypy import *
#from .core import *

import sys
#sys.modules.setdefault('numpy', sys.modules['numpypy'])

import _numpypy as umath
import multiarray
import numerictypes
sys.modules['numpy.core.multiarray'] = multiarray
sys.modules['numpy.core.umath'] = umath

sys.modules['numerictypes'] = numerictypes
sys.modules['numpy.core.numerictypes'] = numerictypes

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
