# indirection needed; otherwise the built-in module "termios" shadows
# any file termios.py that would be found in the user dirs
from __builtin_termios import *
from __builtin_termios import __doc__
