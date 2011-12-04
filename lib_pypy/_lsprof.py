# indirection needed; otherwise the built-in module "_lsprof" shadows
# any file _lsprof.py that would be found in the user dirs
from __builtin__lsprof import *
