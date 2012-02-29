import py
import pypy.translator.jvm.jvm_interop # side effects!
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin

try:
    import jpype
except ImportError:
    py.test.skip("No JPype found, so I'm assuming you're not interested in rjvm.")

from pypy.rlib.rjvm import java, JvmClassWrapper, JvmInstanceWrapper, JvmMethodWrapper, \
    JvmStaticMethodWrapper, JvmPackageWrapper

def test_static_method():
    assert isinstance(java.lang, JvmPackageWrapper)
    assert isinstance(java.lang.Math, JvmClassWrapper)
    assert isinstance(java.lang.Math.abs, JvmStaticMethodWrapper)
    result = java.lang.Math.abs(-42)
    assert isinstance(result, int)
    assert result == 42

def test_invalid_static_method():
    with py.test.raises(TypeError):
        java.lang.Math.typo(42)

def test_invalid_class_name():
    with py.test.raises(TypeError):
        java.lang.Typo()

def test_class_instantiate():
    al = java.util.ArrayList()
    assert isinstance(al, JvmInstanceWrapper)
    assert isinstance(al.add, JvmMethodWrapper)
    al.add("test")
    assert al.get(0) == "test"

def test_invalid_method_name():
    al = java.util.ArrayList()
    al.add("test")
    with py.test.raises(TypeError):
        al.typo(0)


def test_reflection():
    al_class = java.lang.Class.forName("java.util.ArrayList")
    assert isinstance(al_class, JvmInstanceWrapper)
    constructors = al_class.getDeclaredConstructors()
    meths = al_class.getDeclaredMethods()
    empty_constructor, = (c for c in constructors if len(c.getParameterTypes()) == 0)
    al = empty_constructor.newInstance([])
    assert isinstance(al, JvmInstanceWrapper)
    assert isinstance(al.add, JvmMethodWrapper)
    al_clear, = (m for m in meths if m.getName() == 'clear')
    assert isinstance(al_clear, JvmInstanceWrapper)
    assert isinstance(al_clear.invoke, JvmMethodWrapper)
    al.add(7)
    assert al.size() == 1
    al_clear.invoke(al, [])
    assert al.isEmpty()
    al_add, = (m for m in meths if m.getName() == 'add' and len(m.getParameterTypes()) == 1)
    assert isinstance(al_add, JvmInstanceWrapper)
    assert isinstance(al_add.invoke, JvmMethodWrapper)
    al_add.invoke(al, ["Hello"])
    assert al.get(0) == "Hello"


class BaseTestRJVM(BaseRtypingTest):
    def test_simple_constructor(self):
        def fn():
            sb = java.lang.StringBuilder()
        res = self.interpret(fn, [])
        assert res is None

    def test_constructor_args(self):
        def fn():
            sb = java.lang.StringBuilder('foobar')
        res = self.interpret(fn, [])
        assert res is None

    def test_constructor_wrong_args(self):
        def fn():
            sb = java.lang.StringBuilder(7.5)

        with py.test.raises(TypeError):
            self.interpret(fn, [])

    def test_invalid_method(self):
        def fn():
            sb = java.lang.StringBuilder()
            sb.foobar()

        with py.test.raises(TypeError):
            self.interpret(fn, [])

    def test_method_call_no_overload(self):
        def fn():
            t = java.lang.Thread()
            t.setName('foo')
            return t.getName()
        res = self.ll_to_string(self.interpret(fn, []))
        assert res == 'foo'

    def test_method_call_overload(self):
        def fn():
            sb = java.lang.StringBuilder()
            sb.append('foo ')
            sb.append(7)
            return sb.toString()
        res = self.ll_to_string(self.interpret(fn, []))
        assert res == 'foo 7'

    def test_method_call_bad_overload(self):
        def fn():
            sb = java.lang.StringBuilder()
            sb.insert('foo', 'bar')
        with py.test.raises(TypeError):
            self.interpret(fn, [])

    def test_instance_fields(self):
        py.test.skip(
            "Turns out JPype has a 'feature' that calls point.getX() in the code below. "
            "This breaks the test, since getX() returns a double instead of an int for some reason. "
            "I don't think there's much point working on this, since java.awt.Point was the only class "
            "I could find that uses raw instance fields anyway...")
        def fn():
            point = java.awt.Point(42,17)
            point.y = 42
            return point.x

        res = self.interpret(fn, [])
        assert res == 42

class TestRJVM(BaseTestRJVM, OORtypeMixin):
    pass
