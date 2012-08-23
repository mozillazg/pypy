

import sys
import math as _math
#sys.modules.setdefault('numpy', sys.modules['numpypy'])

import _numpypy
umath = _numpypy

import multiarray
sys.modules['multiarray'] = multiarray
sys.modules['numpy.core.multiarray'] = multiarray
sys.modules['umath'] = umath
sys.modules['numpy.core.umath'] = _numpypy

import numerictypes
sys.modules['numerictypes'] = numerictypes
sys.modules['numpy.core.numerictypes'] = numerictypes

import scalarmath
sys.modules['scalarmath'] = scalarmath
sys.modules['numpy.core.scalarmath'] = scalarmath

import _compiled_base
sys.modules['_compiled_base'] = _compiled_base
sys.modules['numpy.lib._compiled_base'] = _compiled_base


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

def not_implemented_func(*args, **kwargs):
    raise NotImplementedError("implemented yet")

setattr(_numpypy, 'frompyfunc', not_implemented_func)
setattr(_numpypy, 'mod', not_implemented_func)
setattr(_numpypy, 'conjugate', not_implemented_func)
setattr(multiarray, '_flagdict', not_implemented_func)
setattr(multiarray, 'flagsobj', not_implemented_func)

#mangle the __all__ of numpy.core so that import numpy.core.numerictypes works
from numpy import core
core.__all__ += ['multiarray', 'numerictypes', 'umath']
core.numerictypes = numerictypes
core.complexfloating = None

#goal: use local lapack_lite for "from numpy.linalg import lapack_lite" 
# problem: import numpy.lib imports polynomial which imports linalg. If I import numpy.linalg, it will
# import numpy.lib and try to import itself agian, before I can set lapack_lite
# 
import linalg
sys.modules['numpy.linalg'] = linalg

import fftpack_lite
sys.modules['fftpack_lite'] = fftpack_lite

import mtrand
sys.modules['mtrand'] = mtrand

sys.modules['ma'] = mtrand
sys.modules['matrixlib'] = mtrand



