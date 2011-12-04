# indirection needed; otherwise the built-in module "_winreg" shadows
# any file _winreg.py that would be found in the user dirs
from __builtin__winreg import *
