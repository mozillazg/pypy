# indirection needed; otherwise the built-in module "unicodedata" shadows
# any file unicodedata.py that would be found in the user dirs
from __builtin_unicodedata import *
from __builtin_unicodedata import _get_code
