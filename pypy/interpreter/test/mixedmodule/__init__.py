from pypy.interpreter.newmodule import ExtModule 

class Module(ExtModule): 
    interpleveldefs = {
        'somefunc' : 'file1.somefunc', 
        'value' : '(space.w_None)', 
    }

    appleveldefs = {
        'someappfunc' : 'file2_app.someappfunc', 
    }
