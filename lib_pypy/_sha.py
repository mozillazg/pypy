# indirection needed; otherwise the built-in module "_sha" shadows
# any file _sha.py that would be found in the user dirs
try:
    from __builtin__sha import *
except ImportError:
    from __sha import *
