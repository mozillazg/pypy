import jpype
import types
from pypy.annotation.model import SomeString, SomeChar, SomeOOInstance
from pypy.rlib import rjvm
from pypy.rpython.ootypesystem import ootype

class ReflectionNameChecker(object):
    """
    Instances of this class can serve as "examples" of native classes. They only have attributes
    that correspond to instance methods of the underlying java class. We have to return an
    instance of ootype._bound_meth to please the rest of the translation process, so we return
    a dummy one to keep things simple.
    """

    dummy_method = ootype._bound_meth(None, None, None)

    def __init__(self, refclass):
        self.refclass = refclass
        self.method_names = {str(m.getName()) for m in refclass.getMethods() if not rjvm._is_static(m)}

    def __getattr__(self, name):
        if name in self.method_names:
            return self.dummy_method
        else:
            raise TypeError("No method called %s found in %s" % (name, self.refclass.getName()))


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

        Here we ignore there 'abstract' versions.
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
                    "We only support very simple scenarios of 'return type overloading"

        ootype.OverloadingResolver.__init__(self, one_method_per_signature.values())

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
        if isinstance(TYPE, types.NativeRJvmInstance):
            return SomeOOInstance(TYPE)
        elif TYPE is ootype.Char:
            return SomeChar()
        elif TYPE is ootype.String:
            return SomeString(can_be_None=True)
        else:
            return ootype.OverloadingResolver.lltype_to_annotation(TYPE)


def jvm_method_to_pypy_method(method, result=None):
    """
    Convert a proxy to a java.lang.reflect.Method to an instance of ootype.meth.
    Sometimes we want to treat constructors as methods to reuse the code that
    handles overloading. In such a case we override the result with ootype.Void
    or whatever (since java.lang.reflect.Constructor has no getReturnType method).
    """
    args = tuple(jpype_type_to_ootype(t) for t in method.getParameterTypes())
    if result is None:
        result = jpype_type_to_ootype(method.getReturnType())
    return ootype.meth(ootype.Meth(args, result))


def jpype_type_to_ootype(tpe):
    assert isinstance(tpe, jpype._jclass._JavaClass)
    try:
        return jpype_primitives_to_ootype_mapping[tpe]
    except KeyError:
        return types.NativeRJvmInstance(tpe.__javaclass__)


jpype_primitives_to_ootype_mapping = {
    jpype.java.lang.Integer.TYPE: ootype.Signed,
    jpype.java.lang.Void.TYPE: ootype.Void,
    jpype.java.lang.String: ootype.String,
}


def has_matching_constructor(jvm_class_wrapper, s_args):
    """
    Create an overloaded method for all the constructors and reuse the code that
    resolves overloadings.
    """
    refclass = jvm_class_wrapper.__reflection_class__
    overloads = [jvm_method_to_pypy_method(c, result=ootype.Void) for c in refclass.getConstructors()]
    overloaded_meth = ootype._overloaded_meth(*overloads, resolver=JvmOverloadingResolver)
    args = tuple(JvmOverloadingResolver.annotation_to_lltype(arg) for arg in s_args)
    try:
        overloaded_meth._resolver.resolve(args)
    except TypeError:
        return False
    else:
        return True


def call_method(method):
    """
    Return a function that when called will "unwrap" arguments (_str('foo') => 'foo'),
    call the method and wrap the result. The returned function can be used as the
    _callable field of an ootype._bound_meth to actually call the method in question.
    """
    def unwrap(value):
        # TODO: what about other primitive types?
        # Is there a general mechanism for this somewhere?
        if isinstance(value, types._native_rjvm_instance):
            return value._instance
        elif isinstance(value, ootype._string):
            return value._str
        else:
            raise AssertionError("Don't know how to unwrap %r" % value)

    def wrap(value):
        if isinstance(value, types.JvmInstanceWrapper):
            return types._native_rjvm_instance(types.NativeRJvmInstance(value.__refclass__), value)
        elif isinstance(value, (str, unicode)):
            return ootype._string(ootype.String, str(value))
        elif value is None:
            return None
        else:
            raise AssertionError("Don't know how to wrap %r" % value)

    def callable(*args):
        args = [unwrap(arg) for arg in args[1:]]   # skip the first arg, method is already bound
        result = method(*args)
        return wrap(result)

    return callable
