# indirection needed; otherwise the built-in module "_locale" shadows
# any file _locale.py that would be found in the user dirs
try:
    from __builtin__locale import *
except ImportError:
    from __locale import *
