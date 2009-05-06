#!/usr/bin/env python

import autopath
import os, sys
from pypy.lang.js.interpreter import load_source, Interpreter, load_file
from pypy.lang.js.jsparser import parse, ParseError
from pypy.lang.js.jsobj import W_Builtin, W_String, ThrowException, w_Undefined
from pypy.rlib.streamio import open_file_as_stream

def printmessage(msg):
    if msg is None:
        return
    os.write(1, msg)

def readline():
    result = []
    while 1:
        s = os.read(0, 1)
        result.append(s)
        if s == '\n':
            break
       
        if s == '':
            if len(result) > 1:
                break
            raise SystemExit
    return ''.join(result)

class JSConsole(object):
    prompt_ok = 'js> '
    prompt_more = '... '

    def __init__(self):
        self.interpreter = Interpreter()
    
    def runsource(self, source, filename='<input>'):
        try:
            ast = load_source(source, filename)
        except ParseError, exc:
            if exc.source_pos.i == len(source):
                # more input needed
                return True
            else:
                # syntax error
                self.showsyntaxerror(filename, exc)
                return False
        
        # execute it
        self.runcode(ast)
        return False
    
    def runcode(self, ast):
        """Run the javascript code in the AST. All exceptions raised
        by javascript code must be caught and handled here. When an
        exception occurs, self.showtraceback() is called to display a
        traceback.
        """
        try:
            res = self.interpreter.run(ast, interactive=True)
            if res is not None and res != w_Undefined:
                try:
                    printmessage(res.ToString(self.interpreter.global_context))
                except ThrowException, exc:
                    printmessage(exc.exception.ToString(self.interpreter.global_context))
                printmessage('\n')
        except SystemExit:
            raise
        #except ThrowException, exc:
        #    self.showtraceback(exc)
    
    def showsyntaxerror(self, filename, exc):
        pass
    
    def interact(self):
        printmessage('PyPy JavaScript Interpreter\n')
        printmessage(self.prompt_ok)
        
        lines = []
        
        while True:
            try:
                line = readline()
            except SystemExit, e:
                printmessage('\n')
                return
            
            lines.append(line)
            
            source = ''.join(lines)
            need_more = self.runsource(source)
            
            if need_more:
                printmessage(self.prompt_more)
            else:
                printmessage(self.prompt_ok)
                lines = []

if __name__ == '__main__':
    console = JSConsole()
    console.interact()
