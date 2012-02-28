from pypy.annotation.model import SomeOOInstance, SomeObject
from pypy.rlib.rjvm import JvmClassWrapper
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.translator.jvm.jvm_interop.types import NativeRJvmInstance
from pypy.translator.jvm.jvm_interop.rtyper import JvmClassWrapperRepr
from pypy.translator.jvm.jvm_interop.utils import has_matching_constructor

class SomeJvmClassWrapper(SomeObject):
    def simple_call(self, *s_args):
        jvm_class_wrapper = self.const
        if not has_matching_constructor(jvm_class_wrapper, s_args):
            raise TypeError('No matching constructor for %s!' % jvm_class_wrapper.__name__)
        return SomeOOInstance(NativeRJvmInstance(jvm_class_wrapper.__reflection_class__))

    def rtyper_makerepr(self, rtyper):
        return JvmClassWrapperRepr(self.const)


class Entry(ExtRegistryEntry):
    """
    Make the annotator aware JvmClassWrappers are "special".
    """
    _type_ = JvmClassWrapper

    def compute_annotation(self):
        return SomeJvmClassWrapper(self.instance)
