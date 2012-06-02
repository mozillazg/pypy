import jpype
import ootypemodel
import pypy.rlib.rjvm as rjvm
import pypy.rlib.rjvm.helpers as helpers
from pypy.annotation.model import SomeString, SomeChar, SomeOOInstance, SomeInteger
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import typeOf


class NativeRJvmInstanceExample(object):
    """
    Instances of this class can serve as "examples" of native classes. They only have attributes
    that correspond to instance (or static) methods and fields of the underlying java class.
    We have to return an instance of ootype._bound_meth to please the rest of the translation process,
    so we return a dummy one to keep things simple.
    """

    def __init__(self, tpe, static=False):
        assert isinstance(tpe, ootypemodel.NativeRJvmInstance)
        self._TYPE = tpe
        self.refclass = tpe.refclass
        self.static = static
        staticness = helpers._check_staticness(static)
        self.method_names = {str(m.getName()) for m in self.refclass.getMethods() if staticness(m)}
        self.field_names = {str(f.getName()) for f in helpers._get_fields(self.refclass, static)}

        # Make dummy_method something that makes sense
        if static:
            self.dummy_method = ootype._overloaded_meth()
        else:
            self.dummy_method = ootype._bound_meth(None, None, None)

    def __getattr__(self, name):
        if name in self.method_names:
            return self.dummy_method
        elif name in self.field_names:
            field = self.refclass.getField(name)
            jtype = field.getType()
            return jpype_type_to_ootype(jtype)._example()
        elif self.static and name == 'class_':
            return ootypemodel.NativeRJvmInstance(helpers.RjvmJavaLangClassWrapper.java_lang_Class)._example()
        else:
            raise TypeError(
                "No method or field called %s found in %s." % (name, self.refclass.getName()))


class JvmOverloadingResolver(ootype.OverloadingResolver):
    def __init__(self, overloadings):
        """
        The problem we have is that sometimes on the bytecode level
        there are methods with the same name and arguments but
        different return types. These are called 'bridge methods'. Here
        we exclude them from the overload finding algorithm.
        """
        one_method_per_signature = {}
        for meth in overloadings:
            METH = typeOf(meth)
            if (isinstance(METH.RESULT, ootypemodel.NativeRJvmInstance) and
                not helpers._is_public(METH.RESULT.refclass)):
                continue

            signature = meth._TYPE.ARGS
            if signature not in one_method_per_signature:
                one_method_per_signature[signature] = meth
            else:
                if METH.is_bridge:
                    continue
                else:
                    one_method_per_signature[signature] = meth

        ootype.OverloadingResolver.__init__(self, one_method_per_signature.values())

    def _can_convert_from_to(self, arg1, arg2):
        # Just the simplest logic for now:
        if isinstance(arg2, ootypemodel.NativeRJvmInstance) and arg2.class_name == 'java.lang.Object':
            # TODO: autoboxing?
            return isinstance(arg1, ootypemodel.NativeRJvmInstance) or arg1 == ootype.String
        return super(JvmOverloadingResolver, self)._can_convert_from_to(arg1, arg2)

    def _get_refclass(self, meth):
        return meth._TYPE.RESULT.refclass

    @classmethod
    def annotation_to_lltype(cls, ann):
        if isinstance(ann, SomeChar):
            return ootype.Char
        elif isinstance(ann, SomeString):
            return ootype.String
        else:
            return ootype.OverloadingResolver.annotation_to_lltype(ann)

    @classmethod
    def lltype_to_annotation(cls, TYPE):
        if isinstance(TYPE, ootypemodel.NativeRJvmInstance):
            return SomeOOInstance(TYPE, can_be_None=True)
        elif TYPE is ootype.Char:
            return SomeChar()
        elif TYPE is ootype.String:
            return SomeString(can_be_None=True)
        else:
            return ootype.OverloadingResolver.lltype_to_annotation(TYPE)


def jvm_method_to_pypy_Meth(method, Meth_type=ootype.Meth, result=None):
    """
    Convert a proxy to a java.lang.reflect.Method to an instance of
    meth_type (defaults to ootype.meth). Sometimes we want to treat
    constructors as methods to reuse the code that handles
    overloading. In such a case we override the result with
    ootype.Void or whatever (since java.lang.reflect.Constructor has
    no getReturnType method).
    """
    args = tuple(jpype_type_to_ootype(t) for t in method.getParameterTypes())
    if result is None:
        result = jpype_type_to_ootype(method.getReturnType())
    res = Meth_type(args, result)
    if hasattr(method, 'isBridge'):
        res.is_bridge = method.isBridge()
    else:
        res.is_bridge = False
    return res


def jvm_method_to_pypy_meth(method, meth_type=ootype.meth, Meth_type=ootype.Meth, result=None):
    return meth_type(jvm_method_to_pypy_Meth(method, Meth_type=Meth_type, result=result))


def jpype_type_to_ootype(tpe):
    assert isinstance(tpe, jpype._jclass._JavaClass)
    if tpe in jpype_primitives_to_ootype_mapping:
        return jpype_primitives_to_ootype_mapping[tpe]
    elif tpe.__javaclass__.isArray():
        refclass = helpers._refclass_for(tpe)
        component_type = refclass.getComponentType()
        res = ootype.Array(ootypemodel.NativeRJvmInstance(component_type))
        return res
    else:
        return ootypemodel.NativeRJvmInstance(tpe)


jpype_primitives_to_ootype_mapping = {
    jpype.java.lang.Integer.TYPE: ootype.Signed,
    jpype.java.lang.Boolean.TYPE: ootype.Bool,
    jpype.java.lang.Double.TYPE: ootype.Float,
    jpype.java.lang.Void.TYPE: ootype.Void,
}


def has_matching_constructor(jvm_class_wrapper, s_args):
    """
    Create an overloaded method for all the constructors and reuse the code that
    resolves overloadings.
    """
    refclass = helpers._refclass_for(jvm_class_wrapper)
    overloads = [jvm_method_to_pypy_meth(c, result=ootype.Void) for c in refclass.getConstructors()]
    overloaded_meth = ootype._overloaded_meth(*overloads, resolver=JvmOverloadingResolver)
    args = tuple(JvmOverloadingResolver.annotation_to_lltype(arg) for arg in s_args)
    try:
        overloaded_meth._resolver.resolve(args)
    except TypeError:
        return False
    else:
        return True


def call_method(jpype_method, pypy_meth, static=False):
    """
    Return a function that when called will "unwrap" arguments (_str('foo') => 'foo'),
    call the method and wrap the result. The returned function can be used as the
    _callable field of an ootype._bound_meth to actually call the method in question.
    """
    def callable(*args):
        start = 0 if static else 1
        arg_types = [typeOf(arg) for arg in args[start:]]
        args = [unwrap(arg) for arg in args[start:]]   # skip the first arg, method is already bound
        if isinstance(pypy_meth, ootype._overloaded_meth):
            result_type = pypy_meth._resolver.result_type_for(arg_types)
        else:
            result_type = typeOf(pypy_meth).RESULT
        result = jpype_method(*args)
        return wrap(result, hint=result_type)

    return callable


def unwrap(value):
    # TODO: what about other primitive types?
    # Is there a general mechanism for this somewhere?
    if isinstance(value, ootypemodel._native_rjvm_instance):
        return value._instance
    elif isinstance(value, ootype._string):
        return value._str
    elif isinstance(value, (int, bool, float)):
        return value
    elif isinstance(value, ootype._array):
        return [unwrap(a) for a in value._array]
    else:
        raise AssertionError("Don't know how to unwrap %r" % value)


def wrap(value, hint=None):
    if isinstance(value, ootypemodel.JvmInstanceWrapper):
        return ootypemodel._native_rjvm_instance(ootypemodel.NativeRJvmInstance(value), value)
    elif isinstance(value, jpype.java.lang.Object):
        return wrap(ootypemodel.JvmInstanceWrapper(value))
    elif isinstance(value, rjvm.jvm_array):
        result = ootype._array(hint, len(value))
        result._array = [wrap(el, hint=hint.ITEM) for el in value]
        return result
    elif isinstance(value, rjvm.jvm_str):
        return ootypemodel._native_rjvm_instance(ootypemodel.NativeRJvmInstance(rjvm.java.lang.String), value)
    elif value is None:
        return ootypemodel._null_native_rjvm_instance(hint)
    elif hint is ootype.Bool and isinstance(value, (int, bool)):
        return bool(value)
    elif hint is ootype.Signed and isinstance(value, (int, float)):
        return int(value)
    elif isinstance(value, (int, float, bool)):
        return value
    else:
        raise AssertionError("Don't know how to wrap %r" % value)


def pypy_method_from_name(refclass, meth_name, meth_type=ootype.meth, Meth_type=ootype.Meth, static=False):
    java_methods = [m for m in helpers._get_methods(refclass, static) if m.getName() == meth_name]

    if not java_methods:
        raise TypeError
    elif len(java_methods) == 1:
        if static:  # return a StaticMethod
            meth = jvm_method_to_pypy_Meth(java_methods[0], Meth_type=Meth_type)
        else:  # return an ootype.meth to be used in _lookup
            meth = jvm_method_to_pypy_meth(java_methods[0], meth_type=meth_type, Meth_type=Meth_type)
    else:
        overloads = [jvm_method_to_pypy_meth(m, meth_type=meth_type, Meth_type=Meth_type) for m in java_methods]
        meth = ootype._overloaded_meth(*overloads, resolver=JvmOverloadingResolver)

    return meth


class Entry(ExtRegistryEntry):
    _about_ = rjvm.new_array

    def compute_result_annotation(self, type_s, length_s):
        assert type_s.is_constant()
        assert isinstance(length_s, SomeInteger)
        TYPE = ootypemodel.NativeRJvmInstance(type_s.const)
        return SomeOOInstance(ootype.Array(TYPE))

    def specialize_call(self, hop):
        assert hop.args_s[0].is_constant()
        TYPE = ootypemodel.NativeRJvmInstance(hop.args_s[0].const)
        vlist = hop.inputconst(ootype.Void, ootype.Array(TYPE))
        vlength = hop.inputarg(ootype.Signed, arg=1)
        hop.exception_is_here()
        return hop.genop('oonewarray', [vlist, vlength],
            resulttype = hop.r_result.lowleveltype)


class Entry(ExtRegistryEntry):
    _about_ = rjvm.downcast

    def compute_result_annotation(self, type_s, inst_s):
        assert type_s.is_constant()
        TYPE = type_s.const
        assert isinstance(TYPE, rjvm.JvmClassWrapper)
        assert isinstance(inst_s, SomeOOInstance)
        assert isinstance(inst_s.ootype, ootypemodel.NativeRJvmInstance)
        return SomeOOInstance(ootypemodel.NativeRJvmInstance(TYPE))

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0].const, rjvm.JvmClassWrapper)
        assert isinstance(hop.args_s[1], SomeOOInstance)
        v_inst = hop.inputarg(hop.args_r[1], arg=1)
        hop.exception_is_here()
        return hop.genop('oodowncast', [v_inst], resulttype = hop.r_result)


class Entry(ExtRegistryEntry):
    _about_ = rjvm.upcast

    def compute_result_annotation(self, type_s, inst_s):
        assert type_s.is_constant()
        TYPE = type_s.const
        assert isinstance(TYPE, rjvm.JvmClassWrapper)
        assert isinstance(inst_s, SomeOOInstance)
        assert isinstance(inst_s.ootype, ootypemodel.NativeRJvmInstance)
        OOTYPE = ootypemodel.NativeRJvmInstance(TYPE)
        assert ootype.isSubclass(inst_s.ootype, OOTYPE)
        return SomeOOInstance(OOTYPE)

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0].const, rjvm.JvmClassWrapper)
        assert isinstance(hop.args_s[1], SomeOOInstance)
        v_inst = hop.inputarg(hop.args_r[1], arg=1)
        hop.exception_cannot_occur()
        return hop.genop('ooupcast', [v_inst], resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = rjvm.native_string

    def compute_result_annotation(self, str_s):
        assert isinstance(str_s, SomeString)
        return SomeOOInstance(ootypemodel.NativeRJvmInstance(rjvm.java.lang.String))

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0], SomeString)
        v_str = hop.inputarg(hop.args_r[0], arg=0)
        hop.exception_cannot_occur()
        return hop.genop('same_as', [v_str], resulttype=ootypemodel.NativeRJvmInstance(rjvm.java.lang.String))

