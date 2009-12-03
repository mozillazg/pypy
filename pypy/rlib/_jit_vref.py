from pypy.annotation import model as annmodel
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.rclass import OBJECTPTR


class SomeVRef(annmodel.SomeObject):

    def __init__(self, s_instance):
        self.s_instance = s_instance

    def simple_call(self):
        return self.s_instance

    def rtyper_makerepr(self, rtyper):
        if not hasattr(rtyper, '_vrefrepr'):
            rtyper._vrefrepr = VRefRepr(rtyper)
        return rtyper._vrefrepr

    def rtyper_makekey(self):
        return self.__class__,


class VRefRepr(Repr):
    def __init__(self, rtyper):
        self.lowleveltype = getinstancerepr(rtyper, None).lowleveltype

    def specialize_call(self, hop):
        [v] = hop.inputargs(getinstancerepr(hop.rtyper, None))
        return v

    def rtype_simple_call(self, hop):
        [v] = hop.inputargs(self)
        v = hop.genop('jit_virtual_force', [v], resulttype = OBJECTPTR)
        return hop.genop('cast_pointer', [v], resulttype = hop.r_result)

# ____________________________________________________________


def jit_virtual_ref(x):
    raise Exception("should not be reached")

class Entry(ExtRegistryEntry):
    _about_ = jit_virtual_ref

    def compute_result_annotation(self, s_obj):
        return SomeVRef(s_obj)

    def specialize_call(self, hop):
        [v] = hop.inputargs(getinstancerepr(hop.rtyper, None))
        return hop.genop('jit_virtual_ref', [v], resulttype = hop.r_result)
