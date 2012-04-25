from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import _static_meth, StaticMethod
from pypy.annotation.model import SomeOOInstance, SomeObject, SomeOOStaticMeth
from pypy.rlib.rjvm import JvmClassWrapper
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.translator.jvm.jvm_interop.ootypemodel import NativeRJvmInstance
import utils


class SomeJvmClassWrapper(SomeObject):
    def simple_call(self, *s_args):
        jvm_class_wrapper = self.const
        if not utils.has_matching_constructor(jvm_class_wrapper, s_args):
            raise TypeError('No matching constructor for %s!' % jvm_class_wrapper.__name__)
        return SomeOOInstance(NativeRJvmInstance(jvm_class_wrapper))

    def getattr(self, s_attr):
        assert self.is_constant()
        assert s_attr.is_constant()
        jvm_class_wrapper = self.const
        attrname = s_attr.const
        refclass = jvm_class_wrapper.class_
        example = utils.NativeRJvmInstanceExample(refclass, static=True)

        if not hasattr(example, attrname):
            raise TypeError("Class %s has no member called %s" % (jvm_class_wrapper.__name__, attrname))

        attr = getattr(example, attrname)
        if isinstance(attr, ootype._meth):
            pypy_meth = utils.pypy_method_from_name(refclass, attrname,
                static=True, meth_type=_static_meth, Meth_type=StaticMethod)
            return SomeJvmNativeStaticMeth(pypy_meth, jvm_class_wrapper, attrname)
        else:
            return utils.JvmOverloadingResolver.lltype_to_annotation(ootype.typeOf(attr))

    def rtyper_makerepr(self, rtyper):
        from rtypemodel import JvmClassWrapperRepr
        return JvmClassWrapperRepr(self.const)


class SomeJvmNativeStaticMeth(SomeOOStaticMeth):
    def __init__(self, method_type, rjvm_class_wrapper, name):
        SomeOOStaticMeth.__init__(self, method_type)
        self.name = name
        self.rjvm_class_wrapper = rjvm_class_wrapper

    def rtyper_makerepr(self, rtyper):
        from rtypemodel import JvmNativeStaticMethRepr
        return JvmNativeStaticMethRepr(self.method, self.name, self.rjvm_class_wrapper)

    def rtyper_makekey(self):
        return self.__class__, self.method


class JvmClassWrapperEntry(ExtRegistryEntry):
    """
    Make the annotator aware JvmClassWrappers are "special".
    """
    _type_ = JvmClassWrapper

    def compute_annotation(self):
        return SomeJvmClassWrapper(self.instance)
