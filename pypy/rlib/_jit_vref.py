from pypy.annotation import model as annmodel
from pypy.annotation.binaryop import _make_none_union
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.error import TyperError


class SomeVRef(annmodel.SomeObject):

    def __init__(self, s_instance):
        self.s_instance = s_instance

    def can_be_none(self):
        return True

    def simple_call(self):
        return self.s_instance

    def rtyper_makerepr(self, rtyper):
        return vrefrepr

    def rtyper_makekey(self):
        return self.__class__,

_make_none_union('SomeVRef', 'obj.s_instance', globals())


class VRefRepr(Repr):
    lowleveltype = OBJECTPTR

    def specialize_call(self, hop):
        [v] = hop.inputargs(getinstancerepr(hop.rtyper, None))
        return v

    def rtype_simple_call(self, hop):
        [v] = hop.inputargs(self)
        v = hop.genop('jit_force_virtual', [v], resulttype = OBJECTPTR)
        return hop.genop('cast_pointer', [v], resulttype = hop.r_result)

    def convert_const(self, value):
        if value:
            raise TyperError("only supports None as a prebuilt virtual_ref")
        return lltype.nullptr(OBJECTPTR.TO)

vrefrepr = VRefRepr()
