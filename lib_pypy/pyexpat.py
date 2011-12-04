# indirection needed; otherwise the built-in module "pyexpat" shadows
# any file pyexpat.py that would be found in the user dirs
try:
    from __builtin_pyexpat import *
except ImportError:
    from _pyexpat import *
