
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
    app = appdef("app(x,y)", """
        return x + y
    """)
    assert app.func_name == 'app'
    w_result = app(space, space.wrap(41), space.wrap(1))
    assert space.eq_w(w_result, space.wrap(42))
