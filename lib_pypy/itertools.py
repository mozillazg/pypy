# indirection needed; otherwise the built-in module "itertools" shadows
# any file itertools.py that would be found in the user dirs
try:
    from __builtin_itertools import *
    from __builtin_itertools import __doc__
except ImportError:
    from _itertools import *
    from _itertools import __doc__
