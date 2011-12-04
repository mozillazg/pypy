# indirection needed; otherwise the built-in module "_hashlib" shadows
# any file _hashlib.py that would be found in the user dirs
from __builtin__hashlib import *
