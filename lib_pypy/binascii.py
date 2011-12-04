# indirection needed; otherwise the built-in module "binascii" shadows
# any file binascii.py that would be found in the user dirs
try:
    from __builtin_binascii import *
except ImportError:
    from _binascii import *
