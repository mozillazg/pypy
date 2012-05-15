from pypy.rlib import rjvm
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import _static_meth, StaticMethod
from pypy.annotation.model import SomeOOInstance, SomeObject, SomeOOStaticMeth, SomeInteger, s_None, s_ImpossibleValue
from pypy.rlib.rjvm import JvmClassWrapper
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.tool.pairtype import pairtype
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
        refclass = rjvm._refclass_for(jvm_class_wrapper)
        example = utils.NativeRJvmInstanceExample(NativeRJvmInstance(jvm_class_wrapper), static=True)

        if not hasattr(example, attrname):
            raise TypeError("Class %s has no member called %s" % (jvm_class_wrapper.__name__, attrname))

        attr = getattr(example, attrname)
        if isinstance(attr, ootype._meth):
            pypy_meth = utils.pypy_method_from_name(refclass, attrname,
                static=True, meth_type=_static_meth, Meth_type=StaticMethod)
            return SomeJvmNativeStaticMeth(pypy_meth, jvm_class_wrapper, attrname)
        else:
            return utils.JvmOverloadingResolver.lltype_to_annotation(ootype.typeOf(attr))

    def rtyper_makekey(self):
        return self.__class__, self.const.__refclass__.getName()

    def rtyper_makerepr(self, rtyper):
        from rtypemodel import JvmClassWrapperRepr
        return JvmClassWrapperRepr(self.const)


class SomeJvmNativeStaticMeth(SomeOOStaticMeth):
    def __init__(self, method_type, jvm_class_wrapper, name):
        SomeOOStaticMeth.__init__(self, method_type)
        self.name = name
        self.jvm_class_wrapper = jvm_class_wrapper

    def rtyper_makerepr(self, rtyper):
        from rtypemodel import JvmNativeStaticMethRepr
        return JvmNativeStaticMethRepr(self.method, self.name, self.jvm_class_wrapper)

    def rtyper_makekey(self):
        return self.__class__, self.name

    def contains(self, other):
        if isinstance(other, SomeJvmNativeStaticMeth):
            return self.name == other.name and \
                   self.jvm_class_wrapper.__name__ == other.jvm_class_wrapper.__name__

        return super(SomeJvmNativeStaticMeth, self).contains(other)


class JvmClassWrapperEntry(ExtRegistryEntry):
    """
    Make the annotator aware JvmClassWrappers are "special".
    """
    _type_ = JvmClassWrapper

    def compute_annotation(self):
        return SomeJvmClassWrapper(self.instance)

class __extend__(pairtype(SomeOOInstance, SomeInteger)):
    def getitem((ooinst, index)):
        if isinstance(ooinst.ootype, ootype.Array):
            # TODO: what about arrays of numbers?
            return SomeOOInstance(ooinst.ootype.ITEM, can_be_None=True)
        return s_ImpossibleValue

    def setitem((ooinst, index), s_value):
        if isinstance(ooinst.ootype, ootype.Array):
            if s_value is s_None:
                return s_None
            assert (ooinst.ootype.ITEM == s_value.ootype or
                    (isinstance(ooinst.ootype.ITEM, NativeRJvmInstance) and
                     isinstance(s_value.ootype, NativeRJvmInstance) and
                     ooinst.ootype.ITEM.class_name == 'java.lang.Object'))
            return s_None
        return s_ImpossibleValue
