import py
from pypy.translator.c.test.test_typed import CompilationTestCase

class WrapperTests(object):
    def test_return_none(self):
        def fn():
            return None
        fn = self.getcompiled(fn, [])
        assert fn() is None

    def test_return_int(self):
        def fn():
            return 1
        fn = self.getcompiled(fn, [])
        assert fn() == 1

    def test_return_float(self):
        def fn():
            return 42.1
        fn = self.getcompiled(fn, [])
        assert fn() == 42.1

    def test_return_true(self):
        def fn():
            return True
        fn = self.getcompiled(fn, [])
        assert fn()

    def test_return_string(self):
        def fn():
            return "hello!"
        fn = self.getcompiled(fn, [])
        assert fn() == "hello!"

    def test_raises_builtin_exception(self):
        def fn():
            raise ValueError
        fn = self.getcompiled(fn, [])
        py.test.raises(ValueError, fn)

    def test_raises_custom_exception(self):
        from pypy.translator.llsupport import modwrapper
        class MyException(Exception):
            pass
        def fn():
            raise MyException
        fn = self.getcompiled(fn, [])
        excinfo = py.test.raises(modwrapper.ExceptionWrapper, fn)
        assert excinfo.value.class_name == "MyException"

    def test_return_list_of_strings(self):
        def f():
            return ['abc', 'def']
        fn = self.getcompiled(f, [])
        assert fn() == ['abc', 'def']

    def test_return_list_of_bools(self):
        def fn():
            return [True, True, False]
        fn = self.getcompiled(fn, [])
        assert fn() == [True, True, False]

    def test_return_tuple_of_list_of_strings(self):
        def fn():
            return ['abc', 'def'],  ['abc', 'def']
        fn = self.getcompiled(fn, [])
        assert fn() == (['abc', 'def'],  ['abc', 'def']) 

    def test_argument_1int(self):
        def fn(x):
            return x + 42
        fn = self.getcompiled(fn, [int])
        assert fn(42) == 84
        assert fn(2) == 44

    def test_argument_2int(self):
        def fn(x, y):
            return x + 42 * y
        fn = self.getcompiled(fn, [int, int])
        assert fn(42, 0) == 42
        assert fn(2, 1) == 44
        assert fn(6, 2) == 90

    def test_argument_string(self):
        def fn(s):
            return len(s)
        fn = self.getcompiled(fn, [str])
        assert fn('aaa') == 3



class TestWrapperRefcounting(CompilationTestCase, WrapperTests):
    pass

from pypy.translator.c.test.test_boehm import AbstractGCTestClass

class TestWrapperMarknSweep(AbstractGCTestClass, WrapperTests):
    gcpolicy = "marksweep"


class TestWrapperBoehm(AbstractGCTestClass, WrapperTests):
    gcpolicy = "boehm"


class TestWrapperSemispace(AbstractGCTestClass, WrapperTests):
    gcpolicy = "semispace"


class TestWrapperGeneration(AbstractGCTestClass, WrapperTests):
    gcpolicy = "generation"
