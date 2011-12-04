# indirection needed; otherwise the built-in module "_minimal_curses" shadows
# any file _minimal_curses.py that would be found in the user dirs
try:
    from __builtin__minimal_curses import *
except ImportError:
    from __minimal_curses import *
