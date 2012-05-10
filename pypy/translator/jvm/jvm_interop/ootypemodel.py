import utils
from pypy.rlib import rjvm
from pypy.rlib.rjvm import JvmInstanceWrapper, JvmPackageWrapper
from pypy.rpython.ootypesystem import ootype


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

    def __repr__(self):
        return '<NativeJvmInstance %s>' % self.class_name

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

    def _field_type(self, field_name):
        self.refclass.getField(field_name)
        return utils.jpype_type_to_ootype(field.getType())

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
        if isinstance(value, ootype._string) and self.class_name == 'java.lang.String':
            return value

#        if isinstance(value, JvmInstanceWrapper) and rjvm._refclass_for(value).getName() == self.class_name:
#            return _native_rjvm_instance(self, value)

        tpe = ootype.typeOf(value)
        if self.class_name == 'java.lang.Object' and tpe == ootype.String or isinstance(tpe, NativeRJvmInstance):
            return value
        else:
            return super(NativeRJvmInstance, self)._enforce(value)

    def _is_string(self):
        return self.class_name == 'java.lang.String'

    def _defl(self, parent=None, parentindex=None):
        return ootype._null_instance(self)

    def __eq__(self, other):
        if isinstance(other, NativeRJvmInstance):
            return self.class_name == other.class_name
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        # This is what ootype.Instance does, I hope it makes sense...
        return object.__hash__(self)

    def __repr__(self):
        return "<NativeRJvmInstance %s>" % self.class_name


class _native_rjvm_instance(object):
    """
    'Executable' version of NativeRJvmInstance.
    """
    def __init__(self, type, instance):
        assert isinstance(type, NativeRJvmInstance)
        assert isinstance(instance, (JvmInstanceWrapper, str))
        self.__dict__['_TYPE'] = type
        self.__dict__['_instance'] = instance
        if isinstance(instance, str):
            self.__dict__['_is_string'] = True

    def __getattr__(self, name):
        assert not isinstance(self._instance, str), "We don't support calling String methods yet."
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
        assert isinstance(self._instance, str)
        return ootype._string(ootype.String, self._instance)

    def __hash__(self):
        # this way strings disguised as _native_rjvm_instances get proper hashes
        return hash(self._instance)

    def __eq__(self, other):
        if isinstance(other, _native_rjvm_instance):
            return self._instance == other._instance
        else:
            return False
