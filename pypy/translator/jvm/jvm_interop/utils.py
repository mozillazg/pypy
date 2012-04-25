import jpype
import ootypemodel
from pypy.annotation.model import SomeString, SomeChar, SomeOOInstance
from pypy.rlib import rjvm
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import typeOf


class NativeRJvmInstanceExample(object):
    """
    Instances of this class can serve as "examples" of native classes. They only have attributes
    that correspond to instance methods and fields of the underlying java class. We have to return an
    instance of ootype._bound_meth to please the rest of the translation process, so we return
    a dummy one to keep things simple.
    """

    def __init__(self, refclass, static=False):
        self.refclass = refclass
        self.static = static
        staticness = check_staticness(static)
        self.method_names = {str(m.getName()) for m in refclass.getMethods() if staticness(m)}
        self.field_names = {str(f.getName()) for f in rjvm._get_fields(refclass, static)}

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
        else:
            raise TypeError(
                "No method or field called %s found in %s." % (name, self.refclass.getName()))


class JvmOverloadingResolver(ootype.OverloadingResolver):
    def __init__(self, overloadings):
        """The problem we have is that sometimes on the bytecode level
        there are methods with the same name and arguments but
        different return types. For instance, for every abstract
        method defined in AbstractStringBuilder that returns an
        AbstractStringBuilder, the 'real' StringBuilder defines a
        method that returns a StringBuilder. The javac compiler is
        smart enough to also generate a second method, which has
        AbstractStringBuilder as the return type (to provide an
        implementation of the abstract method) and only calls the
        'concrete' version. Then the compiler emits code to the
        'concrete' version when you actually call sb.append("foo").

        Here we ignore these 'abstract' versions.
        """
        one_method_per_signature = dict()
        for meth in overloadings:
            signature = meth._TYPE.ARGS
            if not signature in one_method_per_signature:
                one_method_per_signature[signature] = meth
            else:
                refclass = self._get_refclass(meth)
                other_refclass = self._get_refclass(one_method_per_signature[signature])
                if refclass.getSuperclass().getName() == other_refclass.getName():
                    one_method_per_signature[signature] = meth
                else:
                    assert other_refclass.getSuperclass().getName() == refclass.getName(),\
                    "We only support very simple scenarios of 'return type overloading'"

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
            return SomeOOInstance(TYPE)
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
    result = Meth_type(args, result)
    return result


def jvm_method_to_pypy_meth(method, meth_type=ootype.meth, Meth_type=ootype.Meth, result=None):
    return meth_type(jvm_method_to_pypy_Meth(method, Meth_type=Meth_type, result=result))


def jpype_type_to_ootype(tpe):
    assert isinstance(tpe, jpype._jclass._JavaClass)
    try:
        return jpype_primitives_to_ootype_mapping[tpe]
    except KeyError:
        return ootypemodel.NativeRJvmInstance(tpe)


jpype_primitives_to_ootype_mapping = {
    jpype.java.lang.Integer.TYPE: ootype.Signed,
    jpype.java.lang.Boolean.TYPE: ootype.Bool,
    jpype.java.lang.Void.TYPE: ootype.Void,
    jpype.java.lang.String: ootype.String,
}


def has_matching_constructor(jvm_class_wrapper, s_args):
    """
    Create an overloaded method for all the constructors and reuse the code that
    resolves overloadings.
    """
    refclass = jvm_class_wrapper.class_
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
    else:
        raise AssertionError("Don't know how to unwrap %r" % value)


def wrap(value, hint=None):
    if isinstance(value, ootypemodel.JvmInstanceWrapper):
        return ootypemodel._native_rjvm_instance(ootypemodel.NativeRJvmInstance(value), value)
    elif isinstance(value, (str, unicode)):
        return ootype._string(ootype.String, str(value))
    elif value is None:
        return None
    elif isinstance(value, (int, bool, float)):
        # There's only one "special case"/JPype inconsistency for now
        if hint is ootype.Bool:
            return bool(value)
        else:
            return value
    else:
        raise AssertionError("Don't know how to wrap %r" % value)


def pypy_method_from_name(refclass, meth_name, meth_type=ootype.meth, Meth_type=ootype.Meth, static=False):
    java_methods = [m for m in rjvm._get_methods(refclass, static) if m.getName() == meth_name]

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


def check_staticness(should_be_static):
    if should_be_static:
        return rjvm._is_static
    else:
        return lambda m: not rjvm._is_static(m)
