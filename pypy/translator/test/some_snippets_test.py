""" 

    Use all functions in snippet to test translation to pyrex
    
"""
import autopath
import traceback
from pypy.tool import testit
from pypy.translator.translator import Translator

from pypy.translator.test import snippet

import inspect

def compile(func,argtypes=[]):
    
    t = Translator(func)
    t.simplify()
    t.annotate(argtypes)#.simplify()
    #t.view()
    compiled_function = t.compile()
    return compiled_function

def compile_by_inspecting(module):
    bad=0
    good=0
    funcs={}
    all=module.__dict__.items()
    for fu in all:
        if isinstance(fu[1],type(compile)):
            func_info={}
            func_versions={}
            try:
                args=inspect.getargspec(fu[1])
                func_info['arg_names']=args[0]
                func_info['name']=fu[0]
                func_versions['python']=fu[1]
                func_versions['pyrex']=compile(fu[1],[int]*len(args[0]))
            except:
                print fu[0]
                bad+=1
            else:
                good+=1
                funcs[fu[0]]=(func_info,func_versions)
    print "Good: %i, Bad : %i, All: %i"%(good,bad,good+bad) 
    return funcs
def random_arg(arg):
    if arg is int:
        return 5
    if arg is list:
        return [1,2,3,4,5,6] # [1,'ere','fggf']Doesn't work for snippet.yast
    if arg is str:
        return 'python'
    else:
        return 'object'
    
def compile_by_function_info(module,info):
    result={}
    for func_name in info.keys():
        func=module.__dict__[func_name]
        arg_types=info[func_name]['arg_types']
        try:
            pyrex_func=compile(func,arg_types)
        except:
            traceback.print_exc()
            print "Pyrex Compilation exception",func_name
        args=tuple([random_arg(atype) for atype in arg_types])
        try:
            pyresult=func(*args)
            try:
                pyrexresult=pyrex_func(*args)
            except:
                print "pyrex function not runnable",func_name
                raise
        except:
            print "Python Function not runnable",func_name
            print traceback.print_exc()
        else:
            result[func_name]=(pyresult, pyrexresult) #or (pyresult,pyrexresult)
        
    return  result
  
def get_funcs_from_module(module):
    info=module.__dict__.get('function_info',None)
    if info:
        funcs=compile_by_function_info(module,info)
    else:    
        funcs=compile_by_inspecting(module)
    return funcs
    
if __name__=='__main__':
    funcs=get_funcs_from_module(snippet)
    import pprint
    print len(funcs)
    for f in funcs.keys():
        assert funcs[f][0]==funcs[f][1],"%s!=%s"%(funcs[f][0],funcs[f][1])
        print f,
        pprint.pprint(funcs[f])
    
    
