"""
This module supports raw storage of arbitrary data (GC ptr, instance, float,
int) into a void *.
"""

from pypy.annotation import model as annmodel
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rpython.rmodel import Repr


class UntypedStorage(object):
    def __init__(self, n):
        self.storage = [None] * n

    def getint(self, idx):
        v = self.storage[idx]
        assert isinstance(v, int)
        return v

    def setint(self, idx, v):
        assert isinstance(v, int)
        self.storage[idx] = v

    # def getfloat(self, idx, f):
    #     return self.storage[idx]

    # def setfloat(self, idx, f):
    #     self.storage[idx] = f

    def getinstance(self, cls, idx):
        obj = self.storage[idx]
        assert isinstance(obj, cls)
        return obj

    def setinstance(self, idx, obj):
        self.storage[idx] = obj

class UntypedStorageEntry(ExtRegistryEntry):
    _about_ = UntypedStorage

    def compute_result_annotation(self, s_n):
        assert annmodel.SomeInteger().contains(s_n)
        return SomeUntypedStorage()

    def specialize_call(self, hop):
        return hop.r_result.rtyper_new(hop)


class SomeUntypedStorage(annmodel.SomeObject):
    def rtyper_makerepr(self, rtyper):
        return UntypedStorageRepr()

    def method_getint(self, s_idx):
        assert annmodel.SomeInteger().contains(s_idx)
        return annmodel.SomeInteger()

    def method_setint(self, s_idx, s_v):
        assert annmodel.SomeInteger().contains(s_idx)
        assert annmodel.SomeInteger().contains(s_v)

class UntypedStorageRepr(Repr):
    lowleveltype = lltype.Ptr(lltype.GcArray(lltype.Signed))

    def rtyper_new(self, hop):
        [v_arg] = hop.inputargs(lltype.Signed)
        return hop.gendirectcall(self.ll_new, v_arg)

    def rtype_method_getint(self, hop):
        [v_arr, v_idx] = hop.inputargs(self, lltype.Signed)
        return hop.genop("getarrayitem", [v_arr, v_idx], resulttype=lltype.Signed)

    def rtype_method_setint(self, hop):
        [v_arr, v_idx, v_value] = hop.inputargs(self, lltype.Signed, lltype.Signed)
        hop.genop("setarrayitem", [v_arr, v_idx, v_value])

    @classmethod
    def ll_new(cls, size):
        return lltype.malloc(cls.lowleveltype.TO, size)