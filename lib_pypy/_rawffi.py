# indirection needed; otherwise the built-in module "_rawffi" shadows
# any file _rawffi.py that would be found in the user dirs
from __builtin__rawffi import *
