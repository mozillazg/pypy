from pypy.annotation import model as annmodel
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr


class SomeVRef(annmodel.SomeObject):

    def __init__(self, s_instance):
        self.s_instance = s_instance

    def simple_call(self):
        return self.s_instance

    def rtyper_makerepr(self, rtyper):
        return get_vref(rtyper)

    def rtyper_makekey(self):
        return self.__class__,


def specialize_call(hop):
    [v] = hop.inputargs(getinstancerepr(hop.rtyper, None))
    return v

def get_vref(rtyper):
    if not hasattr(rtyper, '_vrefrepr'):
        rtyper._vrefrepr = VRefRepr(rtyper)
    return rtyper._vrefrepr


class VRefRepr(Repr):
    def __init__(self, rtyper):
        self.lowleveltype = getinstancerepr(rtyper, None).lowleveltype

    def rtype_simple_call(self, hop):
        [v] = hop.inputargs(self)
        return hop.genop('cast_pointer', [v], resulttype = hop.r_result)
