# indirection needed; otherwise the built-in module "_ssl" shadows
# any file _ssl.py that would be found in the user dirs
from __builtin__ssl import *
