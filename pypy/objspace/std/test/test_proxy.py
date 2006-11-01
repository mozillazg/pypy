
""" test transparent proxy features
"""

class AppTestProxy(object):
    def test_proxy(self):
        lst = proxy(list, lambda : None)
        assert type(lst) is list

    def test_proxy_repr(self):
        def controller(name, *args):
            lst = [1,2,3]
            if name == '__repr__':
                return repr(lst)
        
        lst = proxy(list, controller)
        assert repr(lst) == repr([1,2,3])

    def test_proxy_append(self):
        class Controller(object):
            def __init__(self, obj):
                self.obj = obj
    
            def perform(self, name, *args):
                return getattr(self.obj, name)(*args)

        c = Controller([])
        lst = proxy(list, c.perform)
        lst.append(1)
        lst.append(2)
        assert repr(lst) == repr([1,2])
