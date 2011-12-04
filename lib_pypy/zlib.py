# indirection needed; otherwise the built-in module "zlib" shadows
# any file zlib.py that would be found in the user dirs
from __builtin_zlib import *
