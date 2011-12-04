# indirection needed; otherwise the built-in module "cx_Oracle" shadows
# any file cx_Oracle.py that would be found in the user dirs
from __builtin_cx_Oracle import *
