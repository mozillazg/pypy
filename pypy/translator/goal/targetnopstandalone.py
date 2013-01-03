"""
A simple standalone target.

The target below specifies None as the argument types list.
This is a case treated specially in driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""

# __________  Entry point  __________

class A(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

def entry_point(argv):
    if len(argv) > 2:
        d = {}
        a = None
        for i in range(int(argv[1])):
            if i % 100 == 0:
                a = A(i, i, i)
            d[i] = a
    else:
        from pypy.rlib import dict
        d = dict.Dict()
        a = None
        for i in range(int(argv[1])):
            if i % 100 == 0:
                a = A(i, i, i)
            d.__setitem__(i, a)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
