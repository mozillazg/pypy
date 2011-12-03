# indirection needed; otherwise the built-in module "_collections" shadows
# any file _collections.py that would be found in the user dirs
try:
    from __builtin__collections import *
except ImportError:
    from __collections import *
