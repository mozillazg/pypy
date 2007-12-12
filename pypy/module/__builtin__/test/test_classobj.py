
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

    def test_mutate_class_special(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
        A.__name__ = 'B'
        assert A.__name__ == 'B'
        assert A.a == 1
        A.__dict__ = {'a': 5}
        assert A.a == 5
        class B:
            __metaclass__ = nclassobj
            a = 17
            b = 18
        class C(A):
            c = 19
        assert C.a == 5
        assert C.c == 19
        C.__bases__ = (B, )
        assert C.a == 17
        assert C.b == 18
        assert C.c == 19
        C.__bases__ = (B, A)
        assert C.a == 17
        assert C.b == 18
        assert C.c == 19
        C.__bases__ = (A, B)
        assert C.a == 5
        assert C.b == 18
        assert C.c == 19

    def test_class_repr(self):
        class A:
            __metaclass__ = nclassobj
        assert repr(A).startswith("<class __builtin__.A at 0x")
        A.__name__ = 'B'
        assert repr(A).startswith("<class __builtin__.B at 0x")
        A.__module__ = 'foo'
        assert repr(A).startswith("<class foo.B at 0x")
        A.__module__ = None
        assert repr(A).startswith("<class ?.B at 0x")
        del A.__module__
        assert repr(A).startswith("<class ?.B at 0x")

    def test_class_str(self):
        class A:
            __metaclass__ = nclassobj
        assert str(A) == "__builtin__.A"
        A.__name__ = 'B'
        assert str(A) == "__builtin__.B"
        A.__module__ = 'foo'
        assert str(A) == "foo.B"
        A.__module__ = None
        assert str(A) == "B"
        del A.__module__
        assert str(A) == "B"

    def test_del_error_class_special(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
        raises(TypeError, "del A.__name__")
        raises(TypeError, "del A.__dict__")
        raises(TypeError, "del A.__bases__")

    def test_mutate_instance_special(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
        class B:
            __metaclass__ = nclassobj
            a = 17
            b = 18
        a = A()
        assert isinstance(a, A)
        a.__class__ = B
        assert isinstance(a, B)
        assert a.a == 17
        assert a.b == 18


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

    def test_len_getsetdelitem(self):
        class A:
            __metaclass__ = nclassobj
        a = A()
        raises(AttributeError, len, a)
        raises(AttributeError, "a[5]")
        raises(AttributeError, "a[5] = 5")
        raises(AttributeError, "del a[5]")
        class A:
            __metaclass__ = nclassobj

        class A:
            __metaclass__ = nclassobj
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __len__(self):
                return len(self.list)
            def __getitem__(self, i):
                return self.list[i]
            def __setitem__(self, i, v):
                self.list[i] = v
            def __delitem__(self, i):
                del self.list[i]

        a = A()
        assert len(a) == 5
        del a[0]
        assert len(a) == 4
        assert a[0] == 2
        a[0] = 5
        assert a[0] == 5
        assert a
        assert bool(a) == True
        del a[0]
        del a[0]
        del a[0]
        del a[0]
        assert len(a) == 0
        assert not a
        assert bool(a) == False

    def test_len_errors(self):
        class A:
            __metaclass__ = nclassobj
            def __len__(self):
                return long(10)
        raises(TypeError, len, A())
        class A:
            __metaclass__ = nclassobj
            def __len__(self):
                return -1
        raises(ValueError, len, A())

    def test_call(self):
        class A:
            __metaclass__ = nclassobj
        a = A()
        raises(AttributeError, a)
        class A:
            __metaclass__ = nclassobj
            def __call__(self, a, b):
                return a + b
        a = A()
        assert a(1, 2) == 3

    def test_nonzero(self):
        class A:
            __metaclass__ = nclassobj
        a = A()
        assert a
        assert bool(a) == True
        class A:
            __metaclass__ = nclassobj
            def __init__(self, truth):
                self.truth = truth
            def __nonzero__(self):
                return self.truth
        a = A(1)
        assert a
        assert bool(a) == True
        a = A(42)
        assert a
        assert bool(a) == True
        a = A(True)
        assert a
        assert bool(a) == True
        a = A(False)
        assert not a
        assert bool(a) == False
        a = A(0)
        assert not a
        assert bool(a) == False
        a = A(-1)
        raises(ValueError, "assert a")
        a = A("hello")
        raises(TypeError, "assert a")

    def test_repr(self):
        class A:
            __metaclass__ = nclassobj
        a = A()
        assert repr(a).startswith("<__builtin__.A instance at")
        assert str(a).startswith("<__builtin__.A instance at")
        A.__name__ = "Foo"
        assert repr(a).startswith("<__builtin__.Foo instance at")
        assert str(a).startswith("<__builtin__.Foo instance at")
        A.__module__ = "bar"
        assert repr(a).startswith("<bar.Foo instance at")
        assert str(a).startswith("<bar.Foo instance at")
        A.__module__ = None
        assert repr(a).startswith("<?.Foo instance at")
        assert str(a).startswith("<?.Foo instance at")
        del A.__module__
        assert repr(a).startswith("<?.Foo instance at")
        assert str(a).startswith("<?.Foo instance at")
        class A:
            __metaclass__ = nclassobj
            def __repr__(self):
                return "foo"
        assert repr(A()) == "foo"
        assert str(A()) == "foo"

    def test_str(self):
        class A:
            __metaclass__ = nclassobj
            def __str__(self):
                return "foo"
        a = A()
        assert repr(a).startswith("<__builtin__.A instance at")
        assert str(a) == "foo"

    def test_iter(self):
        class A:
            __metaclass__ = nclassobj
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __iter__(self):
                return iter(self.list)
        for i, element in enumerate(A()):
            assert i + 1 == element
        class A:
            __metaclass__ = nclassobj
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __len__(self):
                return len(self.list)
            def __getitem__(self, i):
                return self.list[i]
        for i, element in enumerate(A()):
            assert i + 1 == element

    def test_getsetdelattr(self):
        class A:
            __metaclass__ = nclassobj
            a = 1
            def __getattr__(self, attr):
                return attr.upper()
        a = A()
        assert a.a == 1
        a.__dict__['b'] = 4
        assert a.b == 4
        assert a.c == "C"
        class A:
            __metaclass__ = nclassobj
            a = 1
            def __setattr__(self, attr, value):
                self.__dict__[attr.lower()] = value
        a = A()
        assert a.a == 1
        a.A = 2
        assert a.a == 2
        class A:
            __metaclass__ = nclassobj
            a = 1
            def __delattr__(self, attr):
                del self.__dict__[attr.lower()]
        a = A()
        assert a.a == 1
        a.a = 2
        assert a.a == 2
        del a.A
        assert a.a == 1

    def test_instance_override(self):
        class A:
            __metaclass__ = nclassobj
            def __str__(self):
                return "foo"
        def __str__():
            return "bar"
        a = A()
        assert str(a) == "foo"
        a.__str__ = __str__
        assert str(a) == "bar"

    def test_unary_method(self):
        class A:
            __metaclass__ = nclassobj
            def __pos__(self):
                 return -1
        a = A()
        assert +a == -1
