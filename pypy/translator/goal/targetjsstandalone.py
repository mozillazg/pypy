"""
A simple standalone target for the javascript interpreter.

Usage: js-c [-f] jsourcefile [-f] other_source ...
"""

import sys
from pypy.lang.js.interpreter import *
from pypy.lang.js.console import JSConsole

# __________  Entry point  __________

def run_file(interp, name):
    t = load_file(name)
    interp.run(t)    

def entry_point(argv):
    i = 1
    
    if len(argv) == 1:
        console = JSConsole()
        console.interact()
        return 0
    
    interp = Interpreter()
    while i < len(argv):
        arg = argv[i]
        if arg == '-f':
            if i == len(argv) - 1:
                print __doc__
                return 1
            i += 1
            run_file(interp, argv[i])
        elif arg.startswith('-'):
            print "Unsupported option %s" % arg
            print __doc__
            return 1
        else:
            run_file(interp, argv[i])
        i += 1
    return 0
# _____ Define and setup target ___

def target(driver, args):
    driver.exe_name = 'js-%(backend)s'
    return entry_point, None

if __name__ == '__main__':
    entry_point(sys.argv)
