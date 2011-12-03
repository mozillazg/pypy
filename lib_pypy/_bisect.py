# indirection needed; otherwise the built-in module "_bisect" shadows
# any file _bisect.py that would be found in the user dirs
from __builtin__bisect import *
