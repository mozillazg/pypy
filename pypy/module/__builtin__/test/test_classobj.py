
class AppTestOldstyle(object):
    def test_simple(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
        assert A.__name__ == 'A'
        assert A.__bases__ == ()
        assert A.a == 1
        assert A.__dict__['a'] == 1
        a = A()
        a.b = 2
        assert a.b == 2
        assert a.a == 1
        assert a.__class__ is A
        assert a.__dict__ == {'b': 2}

    def test_init(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
            def __init__(self, a):
                self.a = a
        a = A(2)
        assert a.a == 2

