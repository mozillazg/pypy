from pypy.interpreter.newmodule import ExtModule 

class Module(ExtModule): 
    interpleveldefs = {
        '__name__' : '(space.wrap("mixedmodule"))', 
        '__doc__' : '(space.wrap("mixedmodule doc"))', 
        'somefunc' : 'file1.somefunc', 
        'value' : '(space.w_None)', 
    }

    appleveldefs = {
        'someappfunc' : 'file2_app.someappfunc', 
    }
