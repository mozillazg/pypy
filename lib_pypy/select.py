# indirection needed; otherwise the built-in module "select" shadows
# any file select.py that would be found in the user dirs
from __builtin_select import *
