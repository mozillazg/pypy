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
