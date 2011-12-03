# indirection needed; otherwise the built-in module "operator" shadows
# any file operator.py that would be found in the user dirs
from __builtin_operator import *
