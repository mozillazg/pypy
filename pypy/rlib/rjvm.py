import jpype
import atexit

# Classes from this file allow you to write java code "directly" in
# RPython. Code fragments like "sb = java.lang.StringBuilder()" can be
# executed using regular python with JPype installed, turned into flow
# graphs, rtyped and interpreted or compiled to JVM bytecode.
#
# See test_rjvm.py for examples.

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
        if attr[0].isupper():
            if isinstance(getattr(self.__wrapped__, attr), type):
                return JvmClassWrapper(getattr(self.__wrapped__, attr))
            else:
                raise TypeError("There is no class called %s in package %s" % (attr, self.__javaname__))
        elif isinstance(getattr(self.__wrapped__, attr), jpype.JPackage):
            return JvmPackageWrapper(self.__javaname__ + '.' + attr)
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
        if isinstance(item, jpype.java.lang.Object):
            return JvmInstanceWrapper(item)
        elif isinstance(item, jpype._jclass._JavaClass):
            return JvmInstanceWrapper(item.__javaclass__)
        elif isinstance(item, (tuple, list)):
            return self._wrap_list(item)
        return item

    def _wrap_list(self, lst):
        return [self._wrap_item(x) for x in lst]

class CallableWrapper(Wrapper):
    """
    This is a mixin for objects that delegate the __call__ method to
    self.__wrapped__ (a JPype-level proxy) and wrap the result as an
    rjvm-level wrapper.
    """

    def __call__(self, *args):
        args = [arg.__wrapped__ if isinstance(arg, JvmInstanceWrapper) else arg for arg in args]
        result =  self.__wrapped__(*args)
        return self._wrap_item(result)


class JvmClassWrapper(CallableWrapper):
    """
    These should behave like regular classes, allowing you to create instances and
    call static methods.
    """

    def __init__(self, cls):
        self.__wrapped__ = cls
        self.__reflection_class__ = cls.__javaclass__
        self.__name__ = cls.__name__

        refclass = self.__reflection_class__
        self._static_method_names = {str(m.getName()) for m in refclass.getMethods() if _is_static(m)}

    def __getattr__(self, attr):
        if attr in self._static_method_names:
            return JvmStaticMethodWrapper(getattr(self.__wrapped__, attr))
        else:
            raise TypeError(
                "There's no static method called {method_name} in class {class_name}"\
                " and we don't support static fields yet.".format(
                    method_name=attr, class_name=self.__name__))

    def __repr__(self):
        return '<JvmClassWrapper %s>' % self.__name__


class JvmInstanceWrapper(Wrapper):
    """
    Proxy to a JPype-level object. Uses reflection to check attribute access.
    """

    def __init__(self, obj):
        self.__wrapped__ = obj
        if type(obj).__name__ == 'JavaClass':
            refclass = jpype.java.lang.Class.forName('java.lang.Class').__javaclass__
        else:
            refclass = obj.__javaclass__
        self.__class_name = refclass.getName()
        self.__method_names = {str(m.getName()) for m in refclass.getMethods() if not _is_static(m)}

        self.__field_names = {str(f.getName()) for f in _get_fields(refclass)}
        self.__refclass__ = refclass

    def __getattr__(self, attr):
        if attr in self.__method_names:
            return JvmMethodWrapper(getattr(self.__wrapped__, attr))
        elif attr in self.__field_names:
            return self._wrap_item(getattr(self.__wrapped__, attr))
        else:
            raise TypeError(
                "No instance method called {method_name} found in class {class_name}".format(
                    method_name=attr, class_name=self.__class_name))

    def __repr__(self):
        return '<JvmInstanceWrapper %s>' % self.__wrapped__.__name__


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

def _get_fields(refclass):
    """
    Unfortunately JPype seems to crash when calling getFields() on a JavaClass :/
    For now let's stick to getDeclaredFields() and hope to fix this later...
    """
    return refclass.getDeclaredFields()

jpype.startJVM(jpype.getDefaultJVMPath(), "-ea")
java = JvmPackageWrapper("java")

def cleanup():
    jpype.shutdownJVM()

atexit.register(cleanup)
