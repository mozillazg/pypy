# indirection needed; otherwise the built-in module "bz2" shadows
# any file bz2.py that would be found in the user dirs
from __builtin_bz2 import *
