# indirection needed; otherwise the built-in module "math" shadows
# any file math.py that would be found in the user dirs
from __builtin_math import *
from __builtin_math import __doc__
