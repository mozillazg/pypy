"""
This module supports raw storage of arbitrary data (GC ptr, instance, float,
int) into a void *.
"""

from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
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

    def getinstance(self, idx, cls):
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
    def _check_idx(self, s_idx):
        assert annmodel.SomeInteger().contains(s_idx)

    def rtyper_makerepr(self, rtyper):
        return UntypedStorageRepr()

    def method_getint(self, s_idx):
        self._check_idx(s_idx)
        return annmodel.SomeInteger()

    def method_setint(self, s_idx, s_v):
        self._check_idx(s_idx)
        assert annmodel.SomeInteger().contains(s_v)

    def method_getinstance(self, s_idx, s_cls):
        self._check_idx(s_idx)
        assert isinstance(s_cls, annmodel.SomePBC)
        bookkeeper = getbookkeeper()
        classdef = bookkeeper.getuniqueclassdef(s_cls.const)
        return annmodel.SomeInstance(classdef, can_be_None=True)

    def method_setinstance(self, s_idx, s_obj):
        self._check_idx(s_idx)
        assert isinstance(s_obj, annmodel.SomeInstance)

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

    def rtype_method_getinstance(self, hop):
        v_arr = hop.inputarg(self, arg=0)
        v_idx = hop.inputarg(lltype.Signed, arg=1)
        v_result = hop.genop("getarrayitem", [v_arr, v_idx], resulttype=lltype.Signed)
        v_addr = hop.genop("cast_int_to_adr", [v_result], resulttype=llmemory.Address)
        return hop.genop("cast_adr_to_ptr", [v_addr], resulttype=hop.r_result.lowleveltype)

    def rtype_method_setinstance(self, hop):
        [v_arr, v_idx, v_instance] = hop.inputargs(self, lltype.Signed, hop.args_r[2])
        v_addr = hop.genop("cast_ptr_to_adr", [v_instance], resulttype=llmemory.Address)
        v_result = hop.genop("cast_adr_to_int", [v_addr, hop.inputconst(lltype.Void, "symbolic")], resulttype=lltype.Signed)
        hop.genop("setarrayitem", [v_arr, v_idx, v_result])

    @classmethod
    def ll_new(cls, size):
        return lltype.malloc(cls.lowleveltype.TO, size)