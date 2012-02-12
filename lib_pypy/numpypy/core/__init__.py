from .fromnumeric import *
from .numeric import *

import _numpypy
from .numerictypes import sctypeDict
_numpypy.set_typeDict(sctypeDict)

del _numpypy
del sctypeDict
