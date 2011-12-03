# indirection needed; otherwise the built-in module "_io" shadows
# any file _io.py that would be found in the user dirs
from __builtin__io import *
