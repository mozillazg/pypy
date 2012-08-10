#from _numpypy import *
#from .core import *

import sys, types
#sys.modules.setdefault('numpy', sys.modules['numpypy'])

nt = types.ModuleType('numerictype','fake numerictypes module')
setattr(nt, 'sctypeDict',{})
import _numpypy as umath
import multiarray
sys.modules['numpy.core.multiarray'] = multiarray
sys.modules['numpy.core.umath'] = umath

sys.modules['numerictypes'] = nt
sys.modules['numpy.core.numerictypes'] = nt
