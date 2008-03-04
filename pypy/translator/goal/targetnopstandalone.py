"""
A simple standalone target.

The target below specifies None as the argument types list.
This is a case treated specially in driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""

import os, sys

def debug(msg): 
    os.write(2, "debug: " + msg + '\n')

# __________  Entry point  __________

def foobar(n):
    if n > 0:
        return foobar(n-1)+n
    else:
        return 0

def entry_point(argv):
    try:
        foobar(5000000)
    except RuntimeError:
        debug("bigbig")
    debug("hello world: %d" % foobar(5))
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
