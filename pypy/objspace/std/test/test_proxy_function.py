
""" test proxy on functions and other crazy goodies
"""

from pypy.objspace.std.test.test_proxy import AppProxyBasic

class AppTestProxyFunction(AppProxyBasic):
    def test_function_noargs(self):
        def f():
            return 3
        
        import types
        c = self.Controller(f)
        fun = proxy(types.FunctionType, c.perform)
        assert fun() == f()
    
    def test_simple_function(self):
        def f(x):
            return x
        
        import types
        c = self.Controller(f)
        fun = proxy(types.FunctionType, c.perform)
        assert fun(3) == f(3)
