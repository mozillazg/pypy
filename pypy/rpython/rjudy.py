
from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.rtyper import Repr
from pypy.rpython import rmodel

eci = ExternalCompilationInfo(
    includes = ['Judy.h'],
    libraries = ['Judy']
    )

LL_DICT = rffi.VOIDPP
VALUE_TP = rffi.CArrayPtr(lltype.Signed)

JudyLIns = rffi.llexternal('JudyLIns', [LL_DICT, lltype.Signed, lltype.Signed],
                           VALUE_TP, compilation_info=eci)
JudyLCount = rffi.llexternal('JudyLCount', [rffi.VOIDP, lltype.Signed,
                                            lltype.Signed,
                                            lltype.Signed], lltype.Signed,
                             compilation_info=eci)

class JudyRepr(Repr):
    lowleveltype = LL_DICT
    def __init__(self, rtyper):
        self.rtyper = rtyper

    def rtype_len(self, hop):
        v_dict, = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(ll_dict_len, v_dict)

    def rtype_new(self, hop):
        hop.exception_is_here()
        return hop.gendirectcall(ll_newdict)

    def rtype_method_free(self, hop):
        v_j, = hop.inputargs(self)
        hop.exception_is_here()
        return hop.gendirectcall(ll_free, v_j)

class __extend__(pairtype(JudyRepr, rmodel.Repr)): 
    def rtype_setitem((r_dict, r_key), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, lltype.Signed, lltype.Signed)
        hop.exception_cannot_occur()
        hop.gendirectcall(ll_dict_setitem, v_dict, v_key, v_value)

def ll_newdict():
    carray = lltype.malloc(LL_DICT.TO, 1, flavor='raw')
    carray[0] = lltype.nullptr(rffi.VOIDP.TO)
    return carray

def ll_dict_setitem(dict, key, value):
    addr = JudyLIns(dict, rffi.cast(rffi.VOIDP, key), 0)
    addr[0] = value
    
def ll_dict_len(dict):
    return JudyLCount(dict[0], 0, -1, 0)

def ll_free(dict):
    lltype.free(dict, flavor='raw')
