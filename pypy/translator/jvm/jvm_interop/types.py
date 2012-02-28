from pypy.rlib.rjvm import JvmInstanceWrapper, JvmPackageWrapper, _is_static
from pypy.translator.jvm.jvm_interop.utils import ReflectionNameChecker, jvm_method_to_pypy_method, JvmOverloadingResolver, call_method
from pypy.rpython.ootypesystem import ootype

class NativeRJvmInstance(ootype.NativeInstance):
    """
    An OOType for native java instances. Uses reflection on a remote JVM (using JPype)
    to check attribute access.
    """
    def __init__(self, refclass):
        self.refclass = refclass
        self.class_name = refclass.getName()
        self.name_checker = ReflectionNameChecker(refclass) # used in self._example()

    def __repr__(self):
        return '<NativeJvmInstance %s>' % self.class_name

    def _example(self):
        return self.name_checker

    def _lookup(self, meth_name):
        java_methods = [m for m in self.refclass.getMethods() if not _is_static(m) and m.getName() == meth_name]
        if len(java_methods) == 1:
            meth = jvm_method_to_pypy_method(java_methods[0])
        else:
            overloads = [jvm_method_to_pypy_method(m) for m in java_methods]
            meth = ootype._overloaded_meth(*overloads, resolver=JvmOverloadingResolver)
        return self, meth

    def _make_interp_instance(self, args):
        """
        This is called be ootype.new() to make the _native_rjvm_instance object.
        """
        parts = self.class_name.split('.')
        pkg_name, class_name = '.'.join(parts[:-1]), parts[-1]
        pkg = JvmPackageWrapper(pkg_name)
        clazz = getattr(pkg, class_name)
        instance = clazz(*args)
        return _native_rjvm_instance(self, instance)


class _native_rjvm_instance(object):
    """
    'Executable' version of NativeRJvmInstance.
    """
    def __init__(self, type, instance):
        assert isinstance(type, NativeRJvmInstance)
        assert isinstance(instance, JvmInstanceWrapper)
        self._TYPE = type
        self._instance = instance

    def __getattr__(self, name):
        _, meth = self._TYPE._lookup(name)
        meth._callable = call_method(getattr(self._instance, name))
        return meth._bound(self._TYPE, self)
