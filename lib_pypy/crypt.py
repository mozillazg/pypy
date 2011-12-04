# indirection needed; otherwise the built-in module "crypt" shadows
# any file crypt.py that would be found in the user dirs
from __builtin_crypt import *
