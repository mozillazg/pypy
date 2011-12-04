# indirection needed; otherwise the built-in module "_multiprocessing" shadows
# any file _multiprocessing.py that would be found in the user dirs
from __builtin__multiprocessing import *
