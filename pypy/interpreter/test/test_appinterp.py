
import py
from pypy.interpreter.gateway import appdef 

def test_execwith_novars(space): 
    val = space.appexec([], """ 
    (): 
        return 42 
    """) 
    assert space.eq_w(val, space.wrap(42))

def test_execwith_withvars(space): 
    val = space.appexec([space.wrap(7)], """
    (x): 
        y = 6 * x 
        return y 
    """) 
    assert space.eq_w(val, space.wrap(42))

def test_execwith_compile_error(space): 
    excinfo = py.test.raises(SyntaxError, space.appexec, [], """
    (): 
        y y 
    """)
    assert str(excinfo).find('y y') != -1 

def test_simple_applevel(space):
    app = appdef("""app(x,y): 
        return x + y
    """)
    assert app.func_name == 'app'
    w_result = app(space, space.wrap(41), space.wrap(1))
    assert space.eq_w(w_result, space.wrap(42))

def test_applevel_withdefault(space):
    app = appdef("""app(x,y=1): 
        return x + y
    """)
    assert app.func_name == 'app'
    w_result = app(space, space.wrap(41)) 
    assert space.eq_w(w_result, space.wrap(42))

def test_applevel_noargs(space):
    app = appdef("""app(): 
        return 42 
    """)
    assert app.func_name == 'app'
    w_result = app(space) 
    assert space.eq_w(w_result, space.wrap(42))

def somefunc(arg2=42): 
    return arg2 

def test_app2interp_somefunc(space): 
    app = appdef(somefunc) 
    w_result = app(space) 
    assert space.eq_w(w_result, space.wrap(42))
    

