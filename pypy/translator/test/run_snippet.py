""" 

    Use all functions in snippet to test translation to pyrex
    
"""
import autopath
import traceback
import sys
from pypy.tool import testit
from pypy.translator.translator import Translator

from pypy.translator.test import snippet

class Result:
    def __init__(self, func, argtypes):
        self.func = func 
        self.argtypes = argtypes
        self.r_flow = self.r_annotate = self.r_compile = None 
        for name in 'flow', 'annotate', 'compile':
            method = getattr(self, name)
            resname = 'r_' + name 
            try:
                method()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.excinfo = sys.exc_info()
                setattr(self, resname, False) 
            else:
                setattr(self, resname, True) 
                
    def flow(self):
        self.translator = Translator(func)
        self.translator.simplify()

    def annotate(self):
        self.translator.annotate(self.argtypes)

    def compile(self):
        compiled_function = self.translator.compile()
        return compiled_function
    
def collect_functions(module):
    l = []
    for name, value in vars(module).items():
        if name[0] != '_' and hasattr(value, 'func_code'):
            l.append(value) 
    return l
   
def get_arg_types(func):
    # func_defaults e.g.:  ([int, float], [str, int], int) 
    if func.func_defaults:
        argstypelist = []
        for spec in func.func_defaults:
            if isinstance(spec, tuple):
                spec = spec[0] # use the first type only for the tests
            argstypelist.append(spec)
        yield argstypelist 
    else:
        yield []

# format string for result-lines 
format_str = "%-30s %10s %10s %10s" 

def repr_result(res):
    name = res.func.func_name 
    argtypes = res.argtypes 
    funccall = "%s(%s)" % (name, ", ".join([x.__name__ for x in argtypes]))
    flow = res.r_flow and 'ok' or 'fail' 
    ann = res.r_annotate and 'ok' or 'fail'
    comp = res.r_compile and 'ok' or 'fail'
    return format_str %(funccall, flow, ann, comp)
     
if __name__=='__main__':
    funcs = collect_functions(snippet)
    funcs.insert(0, snippet._attrs) 
    results = []
    print format_str %("functioncall", "flowed", "annotated", "compiled")
    for func in funcs:
        for argtypeslist in get_arg_types(func):
            result = Result(func, argtypeslist) 
            results.append(result) 
            print repr_result(result) 
    
    for res in results:
        print repr_result(res) 
   
     
