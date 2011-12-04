# indirection needed; otherwise the built-in module "_continuation" shadows
# any file _continuation.py that would be found in the user dirs
from __builtin__continuation import *
from __builtin__continuation import __doc__
