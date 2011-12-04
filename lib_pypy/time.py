# indirection needed; otherwise the built-in module "time" shadows
# any file time.py that would be found in the user dirs
from __builtin_time import *
