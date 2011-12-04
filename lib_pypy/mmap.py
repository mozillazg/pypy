# indirection needed; otherwise the built-in module "mmap" shadows
# any file mmap.py that would be found in the user dirs
from __builtin_mmap import *
