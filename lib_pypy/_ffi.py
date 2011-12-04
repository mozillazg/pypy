# indirection needed; otherwise the built-in module "_ffi" shadows
# any file _ffi.py that would be found in the user dirs
from __builtin__ffi import *
