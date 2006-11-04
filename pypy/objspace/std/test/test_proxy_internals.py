
""" test proxy internals like code, traceback, frame
"""

class AppTestProxyInternals(object):
    def setup_method(self, meth):
        self.w_get_proxy = self.space.appexec([], """():
        class Controller(object):
            def __init__(self, obj):
                self.obj = obj
    
            def perform(self, name, *args, **kwargs):
                return getattr(self.obj, name)(*args, **kwargs)
        def get_proxy(f):
            return proxy(type(f), Controller(f).perform)
        return get_proxy
        """)

    def test_traceback_basic(self):
        try:
            1/0
        except:
            import sys
            e = sys.exc_info()
        
        tb = self.get_proxy(e[2])
        assert tb.tb_frame is e[2].tb_frame

    def test_traceback_reraise(self):
        #skip("Not implemented yet")
        try:
            1/0
        except:
            import sys
            e = sys.exc_info()
        
        tb = self.get_proxy(e[2])
        raises(ZeroDivisionError, "raise e[0], e[1], tb")
        raises(ZeroDivisionError, "raise e[0], self.get_proxy(e[1]), tb")
        import traceback
        assert len(traceback.format_tb(tb)) == 1
