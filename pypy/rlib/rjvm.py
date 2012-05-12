import os
import jpype
import atexit

# Classes from this file allow you to write java code "directly" in
# RPython. Code fragments like "sb = java.lang.StringBuilder()" can be
# executed using regular python with JPype installed, turned into flow
# graphs, rtyped and interpreted or compiled to JVM bytecode.
#
# See test_rjvm.py for examples.
from pypy.rpython.ootypesystem import ootype

class _jvm_str(object):
    """
    This class reflects the fact, that we don't unify java.lang.String instances with (Some)Strings
    in the ootypesystem. This forces you to call str(...) on native strings.
    """

    def __init__(self, str):
        self.__str = str

    def __str__(self):
        return self.__str

    def __eq__(self, other):
        if isinstance(other, _jvm_str):
            return self.__str == other.__str
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__str)

    def __repr__(self):
        return '<_jvm_str "%s">' % self.__str

    def getClass(self):
        return java.lang.String.class_

class _jvm_array(object):
    def __init__(self, lst):
        self.__lst = lst

    def __setitem__(self, key, value):
        from pypy.translator.jvm.jvm_interop.ootypemodel import _native_rjvm_instance
        assert isinstance(value, JvmInstanceWrapper)
        self.__lst[key] = value

    def __getitem__(self, item):
        return self.__lst[item]

    def __iter__(self):
        return iter(self.__lst)

    def __len__(self):
        return len(self.__lst)

# We want packages to be constant at annotation, so make sure we return the same instances
# for the same names.
const_cache = {}

class JvmPackageWrapper(object):
    """
    Proxy to java packages. You can access atrributes of a
    JvmPackageWrapper to obtain proxies to nested packages or classes
    inside a package. We assume package names start with lowercase
    letters and class names with uppercase.
    """

    def __init__(self, name):
        self.__javaname__ = name
        all_names = name.split(".")
        temp_module = jpype
        for n in all_names:
            temp_module = getattr(temp_module, n)
            assert isinstance(temp_module, jpype.JPackage)
        self.__wrapped__ = temp_module

    def __getattr__(self, attr):
        new_name = self.__javaname__ + '.' + attr
        if attr[0].isupper():
            if isinstance(getattr(self.__wrapped__, attr), type):
                if new_name not in const_cache:
                    const_cache[new_name] = JvmClassWrapper(getattr(self.__wrapped__, attr))
                return const_cache[new_name]
            else:
                raise TypeError("There is no class called %s in package %s" % (attr, self.__javaname__))
        elif isinstance(getattr(self.__wrapped__, attr), jpype.JPackage):
            if new_name not in const_cache:
                const_cache[new_name] = JvmPackageWrapper(new_name)
            return const_cache[new_name]
        else:
            raise AssertionError("getattr on a JPype package should return a another package or a class - right?")

    def _freeze_(self):
        # Treat package wrappers as PBCs at annotation time
        return True

    def __repr__(self):
        return '<JvmPackageWrapper %s>' % self.__javaname__


class Wrapper(object):
    """
    This is a mixin that provides methods to wrap JPype-level types in rjvm-level wrappers.
    """
    def _wrap_item(self, item):
        if isinstance(item, JPypeJavaClass):
            return RjvmJavaLangClassWrapper.forName(item.getName())
        elif isinstance(item, jpype.java.lang.Object):
            return JvmInstanceWrapper(item)
        elif isinstance(item, jpype._jclass._JavaClass):
            return JvmInstanceWrapper(item.__javaclass__)
        elif isinstance(item, (tuple, list)):
            return _jvm_array(self._wrap_list(item))
        elif isinstance(item, (str, unicode)):
            return _jvm_str(str(item))
        elif isinstance(item, jpype._jarray._JavaArrayClass):
            return _jvm_array(self._wrap_list(list(item)))
        elif item is None:
            return None
        return item

    def _wrap_list(self, lst):
        return [self._wrap_item(x) for x in lst]

class CallableWrapper(Wrapper):
    """
    This is a mixin for objects that delegate the __call__ method to
    self.__wrapped__ (a JPype-level proxy) and wrap the result as an
    rjvm-level wrapper.
    """

    def _unwrap_item(self, item):
        if isinstance(item, JvmInstanceWrapper):
            return item.__wrapped__
        elif isinstance(item, (list, _jvm_array)):
            return [self._unwrap_item(i) for i in item]
        elif isinstance(item, ootype._array):
            return self._unwrap_item(item._array)
        elif isinstance(item, _jvm_str):
            return str(item)
        return item

    def __call__(self, *args):
        new_args = [self._unwrap_item(arg) for arg in args]
        try:
            result =  self.__wrapped__(*new_args)
        except RuntimeError, e:
            if e.message.startswith('No matching overloads found'):
                raise TypeError
            else:
                raise
        return self._wrap_item(result)


class JvmClassWrapper(CallableWrapper):
    """
    These should behave like regular classes, allowing you to create instances and
    call static methods.
    """

    def __init__(self, cls):
        self.__wrapped__ = cls
        self.__refclass__ = _refclass_for(cls)
        self.class_ = self._wrap_item(self.__refclass__)
        self.__name__ = cls.__name__

        self._static_method_names = {str(m.getName()) for m in _get_methods(self.__refclass__, static=True)}
        self._static_field_names = {str(f.getName()) for f in _get_fields(self.__refclass__, static=True)}

    def __getattr__(self, attr):
        if attr in self._static_method_names:
            return JvmStaticMethodWrapper(getattr(self.__wrapped__, attr))
        elif attr in self._static_field_names:
            return self._wrap_item(getattr(self.__wrapped__, attr))
        else:
            raise TypeError(
                "There's no static member called {member_name} in class {class_name}.".format(
                    member_name=attr, class_name=self.__name__))

    def __repr__(self):
        return '<JvmClassWrapper %s>' % self.__name__

#    def _freeze_(self):
#        return True


class JvmInstanceWrapper(Wrapper):
    """
    Proxy to a JPype-level object. Uses reflection to check attribute access.
    """

    def __init__(self, obj):
        if isinstance(obj, (JPypeJavaClass, RjvmJavaLangClassWrapper)):
            self.__wrapped__ = _refclass_for(obj)
            refclass = RjvmJavaLangClassWrapper.java_lang_Class
        else:
            self.__wrapped__ = obj
            refclass = _refclass_for(obj)

        self.__refclass = refclass
        self.__class_name = refclass.getName()
        self.__method_names = {str(m.getName()) for m in _get_methods(refclass)}
        self.__field_names = {str(f.getName()) for f in _get_fields(refclass)}

    def __getattr__(self, attr):
        if attr == '__wrapped__':
            return self.__wrapped__
        elif attr in self.__method_names:
            return JvmMethodWrapper(getattr(self.__wrapped__, attr))
        elif attr in self.__field_names:
            return self._wrap_item(getattr(self.__wrapped__, attr))
        else:
            raise TypeError(
                "No instance method called {method_name} found in class {class_name}".format(
                    method_name=attr, class_name=self.__class_name))

    def __repr__(self):
        return '<JvmInstanceWrapper %s>' % self.__wrapped__.__name__

    def _downcast(self, TYPE):
        return self

    def __eq__(self, other):
        if isinstance(other, JvmInstanceWrapper):
            return bool(self.__wrapped__ == other.__wrapped__)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__wrapped__)

class JvmMethodWrapper(CallableWrapper):

    def __init__(self, meth):
        self.__wrapped__ = meth


class JvmStaticMethodWrapper(CallableWrapper):
    def __init__(self, static_meth):
        self.__wrapped__ = static_meth


def _is_static(method_or_field):
    """
    Check if the jpype proxy to a java.lang.reflect.Method (or Field) object
    represents a static method (field).
    """
    return jpype.java.lang.reflect.Modifier.isStatic(method_or_field.getModifiers())

def _is_public(method_or_field):
    return jpype.java.lang.reflect.Modifier.isPublic(method_or_field.getModifiers())

def _get_fields(refclass, static=False):
    staticness = _check_staticness(static)
    return [f for f in refclass.getFields() if staticness(f) and _is_public(f)]

def _get_methods(refclass, static=False):
    staticness = _check_staticness(static)
    return [m for m in refclass.getMethods() if staticness(m) and _is_public(m)]

def _check_staticness(should_be_static):
    if should_be_static:
        return _is_static
    else:
        return lambda m: not _is_static(m)

def _refclass_for(o):
    if isinstance(o, RjvmJavaLangClassWrapper):
        return o
    elif isinstance(o, JvmClassWrapper):
        return o.__refclass__
    elif isinstance(o, JvmInstanceWrapper):
        if isinstance(o.__wrapped__, RjvmJavaLangClassWrapper):
            return RjvmJavaLangClassWrapper.java_lang_Class
        else:
            return _refclass_for(o.__wrapped__)
    elif isinstance(o, JPypeJavaClass):
        return RjvmJavaLangClassWrapper.forName(o.getName())
    elif hasattr(o, '__javaclass__'):
        return _refclass_for(o.__javaclass__)
    else:
        raise TypeError("Bad type for tpe!")

jpype.startJVM(jpype.getDefaultJVMPath(), "-ea",
    "-Djava.class.path=%s" % os.path.abspath(os.path.dirname(__file__)))
java = JvmPackageWrapper("java")
RjvmJavaLangClassWrapper = jpype.JClass('RjvmJavaClassWrapper')
JPypeJavaClass = type(jpype.java.lang.String.__javaclass__)


def new_array(type, size):
    return _jvm_array([None] * size)

def downcast(type, instance):
    assert isinstance(instance, (JvmInstanceWrapper, _jvm_str))
    return instance

int_class = java.lang.Integer.TYPE
long_class = java.lang.Long.TYPE
short_class = java.lang.Short.TYPE
byte_class = java.lang.Byte.TYPE
float_class = java.lang.Float.TYPE
double_class = java.lang.Double.TYPE
boolean_class = java.lang.Boolean.TYPE
char_class = java.lang.Character.TYPE
void_class = java.lang.Void.TYPE

def cleanup():
    jpype.shutdownJVM()

atexit.register(cleanup)

