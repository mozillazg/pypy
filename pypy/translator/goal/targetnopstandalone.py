"""
A simple standalone target.

The target below specifies None as the argument types list.
This is a case treated specially in driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""

import os, sys
from pypy.rpython.lltypesystem import lltype, llmemory

def fib(n):
    if n == 0 or n == 1:
        return n
    else:
        return fib(n-1) + fib(n-2)

def debug(msg): 
    for i in range(36):
        print "n=%d => %d" % (i, fib(i))


# __________  Entry point  __________

def entry_point(argv):
    debug("hello world")
    print llmemory.sizeof(lltype.UniChar)
    if len(argv) > 3:
        raise ValueError
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
