from pypy.rpython.ootypesystem import ootype
import utils
from pypy.annotation.model import SomeOOInstance, SomeObject, s_ImpossibleValue, SomeOOStaticMeth
from pypy.rlib.rjvm import JvmClassWrapper, JvmStaticMethodWrapper, _is_static
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.translator.jvm.jvm_interop.ootypemodel import NativeRJvmInstance
from pypy.translator.jvm.jvm_interop.rtypemodel import JvmClassWrapperRepr
from pypy.translator.jvm.jvm_interop.utils import has_matching_constructor

class SomeJvmClassWrapper(SomeObject):
    def simple_call(self, *s_args):
        jvm_class_wrapper = self.const
        if not has_matching_constructor(jvm_class_wrapper, s_args):
            raise TypeError('No matching constructor for %s!' % jvm_class_wrapper.__name__)
        return SomeOOInstance(NativeRJvmInstance(jvm_class_wrapper.__reflection_class__))

    def getattr(self, s_attr):
        assert self.is_constant()
        assert s_attr.is_constant()
        jvm_class_wrapper = self.const
        attrname = s_attr.const

        if not hasattr(jvm_class_wrapper, attrname):
            return s_ImpossibleValue

        field_or_method = getattr(jvm_class_wrapper, attrname)

        if isinstance(field_or_method, JvmStaticMethodWrapper):
            refclass = jvm_class_wrapper.__reflection_class__
            java_methods = [m for m in refclass.getMethods() if _is_static(m) and m.getName() == attrname]
            if not java_methods:
                raise TypeError
            elif len(java_methods) == 1:
                return SomeOOStaticMeth(utils.jvm_method_to_pypy_Meth(java_methods[0], ootype.StaticMethod))
        else:
            raise AssertionError("Static fields are not yet supported!")

    def rtyper_makerepr(self, rtyper):
        return JvmClassWrapperRepr(self.const)


class JvmClassWrapperEntry(ExtRegistryEntry):
    """
    Make the annotator aware JvmClassWrappers are "special".
    """
    _type_ = JvmClassWrapper

    def compute_annotation(self):
        return SomeJvmClassWrapper(self.instance)
