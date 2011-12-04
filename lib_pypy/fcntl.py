# indirection needed; otherwise the built-in module "fcntl" shadows
# any file fcntl.py that would be found in the user dirs
from __builtin_fcntl import *
