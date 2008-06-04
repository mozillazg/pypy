"""
A simple standalone target for the javascript interpreter.
"""

import sys
from pypy.lang.js.interpreter import *

# __________  Entry point  __________


def entry_point(argv):
    if len(argv) == 2:
        t = load_file(argv[1])
        interp = Interpreter()
        interp.run(t)
        return 0
    else:
        print "Usage: %s jsourcefile" % argv[0]
        return 1

# _____ Define and setup target ___

def target(driver, args):
    driver.exe_name = 'js-%(backend)s'
    return entry_point, None

if __name__ == '__main__':
    entry_point(sys.argv)
