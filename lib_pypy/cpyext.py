# indirection needed; otherwise the built-in module "cpyext" shadows
# any file cpyext.py that would be found in the user dirs
from __builtin_cpyext import *
