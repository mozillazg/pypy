# indirection needed; otherwise the built-in module "cmath" shadows
# any file cmath.py that would be found in the user dirs
from __builtin_cmath import *
from __builtin_cmath import __doc__
