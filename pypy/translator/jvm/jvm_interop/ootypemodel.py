from pypy.rpython.ootypesystem.ootype import _null_mixin
import utils
from pypy.rlib import rjvm
from pypy.rlib.rjvm import JvmInstanceWrapper, JvmPackageWrapper
from pypy.rpython.ootypesystem import ootype

# TODO: cache for NativeRJvmInstance objects.
# For now we only need nulls to be the same.

nulls = {}

class NativeRJvmInstance(ootype.NativeInstance):
    """
    An OOType for native java instances. Uses reflection on a remote JVM
    (using JPype) to check attribute access.
    """
    def __init__(self, tpe):
        self.refclass = rjvm._refclass_for(tpe)
        self.class_name = self.refclass.getName()
        self.field_names = {str(f.getName()) for f in rjvm._get_fields(self.refclass)}
        self.example = utils.NativeRJvmInstanceExample(self)  # used in self._example()
        if self.class_name not in nulls:
            nulls[self.class_name] = _null_native_rjvm_instance(self)
        self._null = nulls[self.class_name]

    @property
    def _superclass(self):
        super_class = self.refclass.getSuperclass()
        if super_class:
            return NativeRJvmInstance(super_class)
        else:
            return None

    def _example(self):
        return self.example

    def _lookup(self, meth_name):
        if isinstance(meth_name, ootype._overloaded_meth_desc):
            # This is only called by the inliner. Returning None stops it from
            # inlining, which is what we want...
            return None, None
        meth = utils.pypy_method_from_name(self.refclass, meth_name)
        return self, meth

    def _check_field(self, field_name):
        return field_name in self.field_names

    def _make_interp_instance(self, args):
        """
        This is called be ootype.new() to make the _native_rjvm_instance object.
        """
        parts = self.class_name.split('.')
        pkg_name, class_name = '.'.join(parts[:-1]), parts[-1]
        pkg = JvmPackageWrapper(pkg_name)
        clazz = getattr(pkg, class_name)
        args = [utils.unwrap(arg) for arg in args]
        instance = clazz(*args)
        return _native_rjvm_instance(self, instance)

    def _enforce(self, value):
        TYPE = ootype.typeOf(value)

        if TYPE == self:
            return value

        if TYPE is ootype.String:
            NATIVE_STRING = NativeRJvmInstance(rjvm.java.lang.String)
            if ootype.isSubclass(NATIVE_STRING, self):
                return _native_rjvm_instance(NATIVE_STRING, rjvm._jvm_str(value._str))
            else:
                raise TypeError
        if (isinstance(TYPE, NativeRJvmInstance) and
              not isinstance(value._instance, rjvm._jvm_str) and
              # object of this type are wrapped in RjvmJavaClassWrapper by rjvm,
              # so the 'shortcut' doesn't work:
              not self.class_name == 'java.lang.Class'):

            if self.refclass.isInstance(value._instance.__wrapped__):
                return value
            else:
                raise TypeError
        elif (isinstance(TYPE, NativeRJvmInstance) and
              # check the subclassing manually for the special cases mentioned above:
              ootype.isSubclass(TYPE, self)):
            return value
        else:
            raise TypeError


    def _is_string(self):
        return self.class_name == 'java.lang.String'

    def _defl(self, parent=None, parentindex=None):
        return self._null

    def __repr__(self):
        return '<NativeJvmInstance %s>' % self.class_name

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        if isinstance(other, NativeRJvmInstance):
            return self.class_name == other.class_name
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    #noinspection PyMethodOverriding
    def __hash__(self):
        return hash(self.class_name)

    def __repr__(self):
        return "<NativeRJvmInstance %s>" % self.class_name


class _native_rjvm_instance(object):
    """
    'Executable' version of NativeRJvmInstance.
    """
    def __init__(self, tpe, instance):
        assert isinstance(tpe, NativeRJvmInstance)
        assert isinstance(instance, (JvmInstanceWrapper, rjvm._jvm_str))
        self.__dict__['_TYPE'] = tpe
        self.__dict__['_instance'] = instance
        if isinstance(instance, rjvm._jvm_str):
            self.__dict__['_is_string'] = True

    def __getattr__(self, name):
        assert not isinstance(self._instance, rjvm._jvm_str), "We don't support calling String methods yet."
        if self._TYPE._check_field(name):
            return utils.wrap(getattr(self._instance, name))
        else:
            _, meth = self._TYPE._lookup(name)
            meth._callable = utils.call_method(getattr(self._instance, name), meth)
            return meth._bound(self._TYPE, self)

    def __setattr__(self, key, value):
        setattr(self._instance, key, value)

    def _downcast(self, TYPE):
        assert ootype.typeOf(self) == TYPE
        return self

    def _string(self):
        assert isinstance(self._instance, rjvm._jvm_str)
        return ootype._string(ootype.String, str(self._instance))

    def __hash__(self):
        # this way strings disguised as _native_rjvm_instances get proper hashes
        return hash(self._instance)

    def __eq__(self, other):
        if isinstance(other, _native_rjvm_instance):
            return self._instance == other._instance
        else:
            return False

    def _upcast(self, TYPE):
        assert isinstance(TYPE, NativeRJvmInstance) and TYPE.class_name == 'java.lang.Object'
        return self

    def __nonzero__(self):
        return self._instance is not None

class _null_native_rjvm_instance(_null_mixin(_native_rjvm_instance), _native_rjvm_instance):
    def __init__(self, TYPE):
        self.__dict__["_TYPE"] = TYPE
