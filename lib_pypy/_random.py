# indirection needed; otherwise the built-in module "_random" shadows
# any file _random.py that would be found in the user dirs
from __builtin__random import *
