import py
import pypy.annotation.model as annmodel
from pypy.rlib import rstring, rarithmetic
import pypy.translator.jvm.jvm_interop as jvm_interop
import pypy.rlib.rjvm as rjvm
from pypy.rlib.rjvm import java
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.annotation.annrpython import RPythonAnnotator

try:
    #noinspection PyUnresolvedReferences
    import jpype
except ImportError:
    py.test.skip("No JPype found, so I'm assuming you're not interested in rjvm.")

jvm_interop.add_registry_entries()


def test_static_method():
    assert isinstance(java.lang, rjvm.JvmPackageWrapper)
    assert isinstance(java.lang.Math, rjvm.JvmClassWrapper)
    assert isinstance(java.lang.Math.abs, rjvm.JvmStaticMethodWrapper)
    result = java.lang.Math.abs(-42)
    assert isinstance(result, int)
    assert result == 42

def test_static_field():
    result = java.lang.Integer.SIZE
    assert isinstance(result, int)
    assert result == 32

def test_invalid_static_member():
    with py.test.raises(TypeError):
        java.lang.Math.typo(42)

def test_invalid_class_name():
    with py.test.raises(TypeError):
        java.lang.Typo()

def test_class_instantiate():
    al = java.util.ArrayList()
    assert isinstance(al, rjvm.JvmInstanceWrapper)
    assert isinstance(al.add, rjvm.JvmMethodWrapper)
    al.add("test")
    assert str(al.get(0)) == "test"

def test_class_repr():
    al = java.util.ArrayList
    assert 'java.util.ArrayList' in repr(al)

def test_instance_repr():
    al = java.util.ArrayList()
    assert 'java.util.ArrayList' in repr(al)

def test_invalid_method_name():
    al = java.util.ArrayList()
    al.add("test")
    with py.test.raises(TypeError):
        al.typo(0)

def test_interpreted_reflection():
    al_class = java.lang.Class.forName("java.util.ArrayList")
    assert isinstance(al_class, rjvm.JvmInstanceWrapper)
    assert isinstance(rjvm.int_class, rjvm.JvmInstanceWrapper)
    assert isinstance(java.util.Collection.class_, rjvm.JvmInstanceWrapper)


    constructors = list(al_class.getConstructors())
    assert len(constructors) == 3

    for types in ([], [rjvm.int_class], [java.util.Collection.class_]):
        c = al_class.getConstructor(types)
        assert isinstance(c, rjvm.JvmInstanceWrapper)
        assert isinstance(c.newInstance, rjvm.JvmMethodWrapper)

    empty_constructor = al_class.getConstructor([])
    al = empty_constructor.newInstance([])
    assert isinstance(al, rjvm.JvmInstanceWrapper)
    assert isinstance(al.add, rjvm.JvmMethodWrapper)

    al_clear = al_class.getMethod('clear', [])
    assert isinstance(al_clear, rjvm.JvmInstanceWrapper)
    assert isinstance(al_clear.invoke, rjvm.JvmMethodWrapper)

    al.add(7)
    assert al.size() == 1

    al_clear.invoke(al, [])
    assert al.isEmpty()
    assert al.size() == 0

    al_add = al_class.getMethod('add', [java.lang.Object.class_])
    assert isinstance(al_add, rjvm.JvmInstanceWrapper)
    assert isinstance(al_add.invoke, rjvm.JvmMethodWrapper)
    al_add.invoke(al, ["Hello"])
    assert str(al.get(0)) == "Hello"


class TestRJvmAnnotation(object):

    def test_strings_are_instances(self):
        def fn():
            o = java.lang.Object()
            return o.toString()

        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)

    def test_str_on_strings(self):
        def fn():
            o = java.lang.Object()
            return str(o.toString())

        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeString)

    def test_returning_string_as_object(self):
        def fn():
            al = java.util.ArrayList()
            al.add('foobar')
            str_as_obj = al.get(0)
            str_as_jstr = rjvm.downcast(java.lang.String, str_as_obj)
            return str_as_jstr

        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)

    def test_intval_is_integer(self):
        def fn():
            b_integer = java.lang.Integer(16)
            integer = b_integer.intValue()
            return integer

        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_intval_is_really_integer(self):
        def fn():
            b1 = rarithmetic.highest_bit(8)
            b2 = rarithmetic.highest_bit(java.lang.Integer(8).intValue())
            return b2

        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeInteger)


    def test_common_type(self):
        def fn(x):
            if x == 1:
                v = java.lang.Integer(17)
            elif x == 2:
                v = java.lang.Boolean(True)
            else:
                v = rjvm.native_string('foobar')
            return v

        a = RPythonAnnotator()
        s = a.build_types(fn, [int])
        assert isinstance(s, annmodel.SomeOOInstance)

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
            return str(t.getName())
        res = self.ll_to_string(self.interpret(fn, []))
        assert res == 'foo'

    def test_method_call_overload(self):
        def fn():
            sb = java.lang.StringBuilder()
            sb.append('foo ')
            sb.append(7)
            return str(sb.toString())
        res = self.ll_to_string(self.interpret(fn, []))
        assert res == 'foo 7'

    def test_method_call_bad_overload(self):
        def fn():
            sb = java.lang.StringBuilder()
            sb.insert('foo', 'bar')
        with py.test.raises(TypeError):
            self.interpret(fn, [])

    def test_get_static_field(self):
        def fn():
            return java.lang.Integer.SIZE, str(java.lang.System.out.toString())

        res = self.interpret(fn, [])
        (a,b) = self.ll_unpack_tuple(res, 2)
        assert a == 32
        assert self.ll_to_string(b).startswith('java.io.PrintStream')

    def test_static_method_no_overload(self):
        def fn():
            return java.lang.Integer.bitCount(5), str(java.util.regex.Pattern.compile('abc').toString())
        (a,b) = self.ll_unpack_tuple(self.interpret(fn, []), 2)
        assert a == 2
        assert self.ll_to_string(b) == 'abc'

    def test_static_method_overload(self):
        def fn():
            return java.lang.Math.abs(-42)
        res = self.interpret(fn, [])
        assert res == 42

    def test_collections(self):
        def fn():
            array_list = java.util.ArrayList()
            array_list.add("one")
            array_list.add("two")
            array_list.add("three")
            return array_list.size()

        res = self.interpret(fn, [])
        assert res == 3

    def test_array_arguments(self):
        """No array covariance for now."""
        def fn():
            o = java.lang.Object()
            java.util.Arrays.asList([o, o, o])

        self.interpret(fn, [])

    def test_array_empty_arguments(self):
        """No array covariance for now."""

        def fn():
            java.util.Arrays.asList(rjvm.new_array(java.lang.Object, 0))

        self.interpret(fn, [])

    def test_array_result(self):
        def fn():
            ms = java.lang.Class.forName('java.lang.Object').getMethods()
            i = 0
            for m in ms:
                i += 1
            return i, len(ms)

        res = self.interpret(fn, [])
        rs = self.ll_unpack_tuple(res, 2)
        assert rs == (9, 9)

    def test_array_setitem(self):
        def fn():
            arr = rjvm.new_array(java.lang.Object, 5)
            o = java.lang.Object()
            arr[2] = o
            return str(arr[2].toString())

        res = self.interpret(fn, [])
        assert self.ll_to_string(res).startswith('java.lang.Object@')

    def test_reflection_for_name(self):
        def fn():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            return str(al_class.getName())

        res = self.interpret(fn, [])
        assert self.ll_to_string(res) == 'java.util.ArrayList'

    def test_reflection_primitive_types(self):
        def fn():
            int_class = java.lang.Integer.TYPE
            return str(int_class.getName())

        res = self.interpret(fn, [])
        assert self.ll_to_string(res) == 'int'

    def test_reflection_get_empty_constructor(self):

        def fn():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            c = al_class.getConstructor(rjvm.new_array(java.lang.Class, 0))
            return c.getModifiers()

        res = self.interpret(fn, [])
        assert res == 1

    def test_reflection_get_int_constructor(self):
        def fn():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            c = al_class.getConstructor([java.lang.Integer.TYPE])
            return c.getModifiers()

        res = self.interpret(fn, [])
        assert res == 1

    def test_reflection_get_collection_constructor_class_literal(self):
        def fn():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            c = al_class.getConstructor([java.util.Collection.class_])
            return c.getModifiers()

        res = self.interpret(fn, [])
        assert res == 1

    def test_reflection_get_collection_constructor_dynamic(self):
        def fn():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            types = rjvm.new_array(java.lang.Class, 1)
            types[0] = java.lang.Class.forName('java.util.Collection')
            c = al_class.getConstructor(types)
            return c.getModifiers()

        res = self.interpret(fn, [])
        assert res == 1

    def test_reflection_instance_creation_no_args(self):
        def fn1():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            c = al_class.getConstructor(rjvm.new_array(java.lang.Class, 0))
            object_al = c.newInstance(rjvm.new_array(java.lang.Object, 0))
            al = rjvm.downcast(java.util.ArrayList, object_al)
            return al.size()

        res = self.interpret(fn1, [])
        assert res == 0

    def test_reflection_instance_creation_array_args(self):
        def fn():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            c = al_class.getConstructor([java.lang.Integer.TYPE])
            args_array = rjvm.new_array(java.lang.Object, 1)
            args_array[0] = java.lang.Integer.valueOf(15)
            object_al = c.newInstance(args_array)
            al = rjvm.downcast(java.util.ArrayList, object_al)
            return al.size()

        res = self.interpret(fn, [])
        assert res == 0

    def test_reflection_instance_creation_arraylist_args(self):
        def fn():
            al_class = java.lang.Class.forName('java.util.ArrayList')
            c = al_class.getConstructor([java.lang.Integer.TYPE])
            args = java.util.ArrayList()
            args.add(java.lang.Integer.valueOf(15))
            args_array = args.toArray()
            object_al = c.newInstance(args_array)
            al = rjvm.downcast(java.util.ArrayList, object_al)
            return al.size()

        res = self.interpret(fn, [])
        assert res == 0

    def test_reflection_method_call(self):
        def fn():
            al = java.util.ArrayList()
            o = java.lang.Object()
            al.add(o)
            al_class = java.lang.Class.forName('java.util.ArrayList')
            size_meth = al_class.getMethod('size', rjvm.new_array(java.lang.Class, 0))
            size = rjvm.downcast(java.lang.Integer, size_meth.invoke(al, rjvm.new_array(java.lang.Object, 0)))
            return size.intValue()

        res = self.interpret(fn, [])
        assert res == 1

    def test_returning_string_as_object(self):
        def fn():
            al = java.util.ArrayList()
            al.add('foobar')
            str_as_obj = al.get(0)
            str_as_jstr = rjvm.downcast(java.lang.String, str_as_obj)
            return str(str_as_jstr)

        res = self.interpret(fn, [])
        assert self.ll_to_string(res) == 'foobar'

    def test_reflection_static_field(self):
        def fn():
            system_class = java.lang.Class.forName('java.lang.System')
            out_field = system_class.getField('out')
            dummy = java.lang.Object()
            out = out_field.get(dummy)
            hashcode_meth = java.lang.Class.forName('java.lang.Object').getMethod('hashCode', rjvm.new_array(java.lang.Class, 0))
            res_as_obj = hashcode_meth.invoke(out, rjvm.new_array(java.lang.Object, 0))
            res_as_integer = rjvm.downcast(java.lang.Integer, res_as_obj)
            return res_as_integer.intValue()

        res = self.interpret(fn, [])
        assert isinstance(res, int)

    def test_method_name(self):
        def fn(s):
            cls = java.lang.Class.forName(s)
            m = cls.getMethods()[0]
            name = m.getName()
            return str(name)

        res = self.interpret(fn, [self.string_to_ll('java.lang.Object')])
        assert isinstance(self.ll_to_string(res), str)

    def test_dicts_of_method_names(self):
        def fn(class_name):
            cls = java.lang.Class.forName(class_name)
            names = {}
            for m in cls.getMethods():
                names[m.getName()] = True
            return len(names)

        res = self.interpret(fn, [self.string_to_ll('java.lang.Object')])
        assert res == 7

    def test_str_on_strings(self):
        def fn():
            o = java.lang.Object()
            return str(o.toString())

        res = self.interpret(fn, [])
        assert self.ll_to_string(res).startswith('java.lang.Object')

    def test_split_on_native_strings(self):
        def fn():
            parts = rstring.split('ala ma kota', ' ')
            b_obj = java.lang.Object()
            b_str = b_obj.toString()
            return rstring.split(str(b_str), '@')[0]

        res = self.interpret(fn, [])
        assert self.ll_to_string(res) == 'java.lang.Object'

    def test_common_type(self):
        def fn(x):
            if x == 1:
                v = java.lang.Integer(17)
            elif x == 2:
                v = java.lang.Boolean(True)
            else:
                v = java.lang.String('foobar')

            return 1 if v else 0

        res = self.interpret(fn, [2])
        assert res == 1

    def test_two_static_method_calls(self):
        def f1():
            v1 = java.lang.reflect.Modifier.isPublic(1)
            v2 = java.lang.reflect.Modifier.isPrivate(1)
            return v1, v2

        res = self.interpret(f1, [])
        (a,b) = self.ll_unpack_tuple(res, 2)
        assert bool(a)
        assert not bool(b)

    def test_code_for_new(self):
        def fn():
            args_w = [(java.awt.Point(), 'java.awt.Point')]

            b_java_cls = java.lang.Class.forName('java.awt.Point')
            types = rjvm.new_array(java.lang.Class, 1)
            args = rjvm.new_array(java.lang.Object, 1)

            for i, w_arg_type in enumerate(args_w):
                w_arg, w_type = w_arg_type
                type_name = w_type
                b_arg = w_arg
                types[i] = java.lang.Class.forName(type_name)
                args[i] = b_arg

            constructor = b_java_cls.getConstructor(types)
            b_obj = constructor.newInstance(args)

        self.interpret(fn, [])

    def test_code_for_get_methods(self):
        def get_methods(class_name):
            b_java_cls = java.lang.Class.forName(class_name)
            result = {}

            for method in b_java_cls.getMethods():

                if method.getName() not in result:
                    result[method.getName()] = []

                return_type_name = str(method.getReturnType().getName())
                arg_types_names = [str(t.getName()) for t in method.getParameterTypes()]

                result[method.getName()].append((return_type_name, arg_types_names))

            i = 0
            for k,v in result.iteritems():
                i += 1
            return i

        res = self.interpret(get_methods, [self.string_to_ll('java.lang.Object')])
        assert res == 7

    def test_null_is_none(self):
        def fn():
            cls = java.lang.Object.class_
            sup = cls.getSuperclass()
            if sup:
                return True
            else:
                return False

        res = self.interpret(fn, [])
        assert res == False

    def test_null_is_none_2(self):
        def fn(b):
            if b:
                v = java.lang.Object()
            else:
                v = None
            return v
        res = self.interpret(fn, [False])

    def test_comparing_classes(self):
        def fn():
            c1 = java.lang.Class.forName('java.lang.String')
            c2 = java.lang.String.class_
            return c1 == c2

        res = self.interpret(fn, [])
        assert res == True

    def test_native_strings(self):
        def fn():
            obj_array = rjvm.new_array(java.lang.Object, 3)
            obj_array[1] = rjvm.native_string('foobar')
            b_str = rjvm.downcast(java.lang.String, obj_array[1])
            return str(b_str)

        res = self.interpret(fn, [])
        assert self.ll_to_string(res) == 'foobar'

class TestRJVM(BaseTestRJVM, OORtypeMixin):
    pass

class TestCPythonRJVM(BaseTestRJVM):
    def interpret(self, fn, args):
        return fn(*args)

    def ll_to_string(self, s):
        assert isinstance(s, str)
        return s

    def ll_unpack_tuple(self, t, size):
        return t

    def string_to_ll(self, s):
        return s

