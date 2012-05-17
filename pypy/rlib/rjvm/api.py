# Classes from this file allow you to write java code "directly" in
# RPython. Code fragments like "sb = java.lang.StringBuilder()" can be
# executed using regular python with JPype installed, turned into flow
# graphs, rtyped and compiled to JVM bytecode.
#
# Testing with LLInterpreter is also supported.
#
# See test_rjvm.py for examples.
import jpype
import helpers
from pypy.rpython.ootypesystem import ootype

class jvm_str(object):
    """
    This class reflects the fact, that we don't unify java.lang.String instances with (Some)Strings.
    This forces you to call str(...) on native strings.
    """

    def __init__(self, str):
        self.__str = str

    def __str__(self):
        return self.__str

    def __eq__(self, other):
        if isinstance(other, jvm_str):
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

class jvm_array(object):
    """
    This class reflects the fact, that we don't unify JVM arrays with (Some)Lists.
    Arrays are not iterable, but support __len__, __getitem__ and __setitem__.
    """
    def __init__(self, lst):
        self.__lst = lst

    def __setitem__(self, key, value):
        assert isinstance(value, (JvmInstanceWrapper, jvm_str))
        self.__lst[key] = value

    def __getitem__(self, item):
        return self.__lst[item]

#    def __iter__(self):
#        return iter(self.__lst)

    def __len__(self):
        return len(self.__lst)

# We want packages to be constant at annotation time, so make sure we return
# the same instances for the same names.
const_cache = {}

class JvmPackageWrapper(object):
    """
    Proxy to java packages. You can access attributes of a
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
        if isinstance(item, helpers.JPypeJavaClass):
            return helpers.RjvmJavaLangClassWrapper.forName(item.getName())
        elif isinstance(item, jpype.java.lang.Object):
            return JvmInstanceWrapper(item)
        elif isinstance(item, jpype._jclass._JavaClass):
            return JvmInstanceWrapper(item.__javaclass__)
        elif isinstance(item, (tuple, list)):
            return jvm_array(self._wrap_list(item))
        elif isinstance(item, (str, unicode)):
            return jvm_str(str(item))
        elif isinstance(item, jpype._jarray._JavaArrayClass):
            return jvm_array(self._wrap_list(list(item)))
        elif item is None:
            return None
        return item

    def _wrap_list(self, lst):
        return [self._wrap_item(x) for x in lst]

class CallableWrapper(Wrapper):
    """
    This is a mixin for objects that delegate the __call__ method to
    self.__wrapped__ (a JPype-level proxy) and wrap the result in an
    rjvm-level wrapper.
    """

    def _unwrap_item(self, item):
        if isinstance(item, JvmInstanceWrapper):
            return item.__wrapped__
        elif isinstance(item, (list, jvm_array)):
            return [self._unwrap_item(i) for i in item]
        elif isinstance(item, ootype._array):
            return self._unwrap_item(item._array)
        elif isinstance(item, jvm_str):
            return str(item)
        return item

    def __call__(self, *args):
        new_args = [self._unwrap_item(arg) for arg in args]
        try:
            result =  self.__wrapped__(*new_args)
        except RuntimeError, e:
            if e.message.startswith("No matching overloads found"):
                raise TypeError("No matching overloads found!")
            else:
                raise
        except jpype.JavaException, e:
            raise helpers.handle_java_exception(e)

        return self._wrap_item(result)


class JvmClassWrapper(CallableWrapper):
    """
    These should behave like regular classes, allowing you to create instances and
    call static methods.
    """

    def __init__(self, cls):
        self.__wrapped__ = cls
        self.__refclass__ = helpers._refclass_for(cls)
        self.class_ = self._wrap_item(self.__refclass__)
        self.__name__ = cls.__name__

        self._static_method_names = {str(m.getName()) for m in helpers._get_methods(self.__refclass__, static=True)}
        self._static_field_names = {str(f.getName()) for f in helpers._get_fields(self.__refclass__, static=True)}

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


class JvmInstanceWrapper(Wrapper):
    """
    Proxy to a JPype-level object. Uses reflection to check attribute access.
    """

    def __init__(self, obj):
        if isinstance(obj, (helpers.JPypeJavaClass, helpers.RjvmJavaLangClassWrapper)):
            self.__wrapped__ = helpers._refclass_for(obj)
            refclass = helpers.RjvmJavaLangClassWrapper.java_lang_Class
        else:
            self.__wrapped__ = obj
            refclass = helpers._refclass_for(obj)

        self.__refclass = refclass
        self.__class_name = refclass.getName()
        self.__method_names = {str(m.getName()) for m in helpers._get_methods(refclass)}
        self.__field_names = {str(f.getName()) for f in helpers._get_fields(refclass)}

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
    __slots__ = ('__wrapped__',)
    def __init__(self, meth):
        self.__wrapped__ = meth


class JvmStaticMethodWrapper(CallableWrapper):
    __slots__ = ('__wrapped__',)
    def __init__(self, static_meth):
        self.__wrapped__ = static_meth


# Main 'entry point' to the package
java = JvmPackageWrapper('java')


class ReflectionException(Exception):
    pass


# These functions get compiled to appropriate JVM instructions:
def new_array(type, size):
    return jvm_array([None] * size)


def downcast(type, instance):
    assert isinstance(instance, (JvmInstanceWrapper, jvm_str))
    return instance


def upcast(type, instance):
    assert isinstance(instance, (JvmInstanceWrapper, jvm_str))
    return instance


def native_string(s):
    """
    Turns a Python string into a java.lang.String instance. In compiled code
    this is a no-op.
    """
    return jvm_str(s)
