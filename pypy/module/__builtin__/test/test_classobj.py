
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
        class B:
            __metaclass__ = nclassobj
            def __init__(self, a):
                return a

        raises(TypeError, B, 2)

    def test_method(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
            def f(self, a):
                return self.a + a
        a = A()
        assert a.f(2) == 3
        assert A.f(a, 2) == 3
        a.a = 5
        assert A.f(a, 2) == 7

    def test_inheritance(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
            b = 2
            def af(self):
                return 1
            def bf(self):
                return 2
        assert A.a == 1
        assert A.b == 2
        a = A()
        assert a.a == 1
        assert a.b == 2
        assert a.af() == 1
        assert a.bf() == 2
        assert A.af(a) == 1
        assert A.bf(a) == 2

        class B(A):
            a = 3
            c = 4
            def af(self):
                return 3
            def cf(self):
                return 4
        assert B.__bases__ == (A, )
        assert B.a == 3
        assert B.b == 2
        assert B.c == 4
        b = B()
        assert b.a == 3
        assert b.b == 2
        assert b.c == 4
        assert b.af() == 3
        assert b.bf() == 2
        assert b.cf() == 4
        assert B.af(b) == 3
        assert B.bf(b) == 2
        assert B.cf(b) == 4

    def test_inheritance_unbound_method(self):
        class A:
            __metaclass__ = nclassobj
            def f(self):
                return 1
        raises(TypeError, A.f, 1)
        assert A.f(A()) == 1
        class B(A):
            pass
        raises(TypeError, B.f, 1)
        raises(TypeError, B.f, A())
        assert B.f(B()) == 1
