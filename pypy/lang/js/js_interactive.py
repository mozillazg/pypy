#!/usr/bin/env python
# encoding: utf-8
"""
js_interactive.py
"""

import autopath
import sys
import getopt
from pypy.lang.js.interpreter import load_source, Interpreter, load_file
from pypy.lang.js.jsparser import parse, ParseError
from pypy.lang.js.jsobj import W_Builtin, W_String, ThrowException, \
                               w_Undefined, W_Boolean
from pypy.rlib.streamio import open_file_as_stream

import code
sys.ps1 = 'js> '
sys.ps2 = '... '

try:
    # Setup Readline
    import readline
    import os
    histfile = os.path.join(os.environ["HOME"], ".jspypyhist")
    try:
        getattr(readline, "clear_history", lambda : None)()
        readline.read_history_file(histfile)
    except IOError:
        pass
    import atexit
    atexit.register(readline.write_history_file, histfile)
except ImportError:
    pass

DEBUG = False

def debugjs(ctx, args, this):
    global DEBUG
    DEBUG = not DEBUG
    return W_Boolean(DEBUG)

def loadjs(ctx, args, this):
    filename = args[0].ToString()
    t = load_file(filename)
    return t.execute(ctx)

def tracejs(ctx, args, this):
    arguments = args
    import pdb
    pdb.set_trace()
    return w_Undefined

def quitjs(ctx, args, this):
    sys.exit(0)
    
class JSInterpreter(code.InteractiveConsole):
    def __init__(self, locals=None, filename="<console>"):
        code.InteractiveConsole.__init__(self, locals, filename)
        self.interpreter = Interpreter()
        ctx = self.interpreter.global_context
        self.interpreter.w_Global.Put(ctx, 'quit', W_Builtin(quitjs))
        self.interpreter.w_Global.Put(ctx, 'load', W_Builtin(loadjs))
        self.interpreter.w_Global.Put(ctx, 'trace', W_Builtin(tracejs))
        self.interpreter.w_Global.Put(ctx, 'debug', W_Builtin(debugjs))

    def runcodefromfile(self, filename):
        f = open_file_as_stream(filename)
        self.runsource(f.readall(), filename)
        f.close()

    def runcode(self, ast):
        """Run the javascript code in the AST. All exceptions raised
        by javascript code must be caught and handled here. When an
        exception occurs, self.showtraceback() is called to display a
        traceback.
        """
        try:
            res = self.interpreter.run(ast, interactive=True)
            if DEBUG:
                print self.interpreter._code
            if res not in (None, w_Undefined):
                try:
                    if DEBUG:
                        print repr(res)
                    print res.ToString(self.interpreter.w_Global)
                except ThrowException, exc:
                    print exc.exception.ToString(self.interpreter.w_Global)
        except SystemExit:
            raise
        except ThrowException, exc:
            self.showtraceback(exc)
        else:
            if code.softspace(sys.stdout, 0):
                print

    def runsource(self, source, filename="<input>"):
        """Parse and run source in the interpreter.

        One of these cases can happen:
        1) The input is incorrect. Prints a nice syntax error message.
        2) The input in incomplete. More input is required. Returns None.
        3) The input is complete. Executes the source code.
        """
        try:
            ast = load_source(source, filename)
        except ParseError, exc:
            if exc.source_pos.i == len(source):
                # Case 2
                return True # True means that more input is needed
            else:
                # Case 1
                self.showsyntaxerror(filename, exc)
                return False

        # Case 3
        self.runcode(ast)
        return False

    def showtraceback(self, exc):
        # XXX format exceptions nicier
        print exc.exception.ToString()

    def showsyntaxerror(self, filename, exc):
        # XXX format syntax errors nicier
        print ' '*4 + \
              ' '*exc.source_pos.columnno + \
              '^'
        print 'Syntax Error:', exc.errorinformation.failure_reasons

    def interact(self, banner=None):
        if banner is None:
            banner = 'PyPy JavaScript Interpreter'
        code.InteractiveConsole.interact(self, banner)

def main(inspect=False, files=[]):
    jsi = JSInterpreter()
    for filename in files:
        jsi.runcodefromfile(filename)
    if (not files) or inspect:
        jsi.interact()

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser(usage='%prog [options] [files] ...',
                          description='PyPy JavaScript Interpreter')
    parser.add_option('-i', dest='inspect',
                    action='store_true', default=False,
                    help='inspect interactively after running script')

    # ... (add other options)
    opts, args = parser.parse_args()

    if args:
        main(inspect=opts.inspect, files=args)
    else:
        main(inspect=opts.inspect)
    sys.exit(0)
