# indirection needed; otherwise the built-in module "_md5" shadows
# any file _md5.py that would be found in the user dirs
try:
    from __builtin__md5 import *
except ImportError:
    from __md5 import *
