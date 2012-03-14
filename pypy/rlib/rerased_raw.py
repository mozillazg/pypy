"""
This module supports raw storage of arbitrary data (GC ptr, instance, float,
int) into a void *.  The creator of the UntypedStorage is responsible for
making sure that the shape string is cached correctly.
"""

from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.rpython.annlowlevel import (hlstr, llstr, llhelper,
    cast_instance_to_base_ptr)
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rpython.lltypesystem.rstr import STR, string_repr
from pypy.rpython.rmodel import Repr
from pypy.tool.pairtype import pairtype


INT = "i"
BOOL = "b"
FLOAT = "f"
INSTANCE = "o"
STRING = "s"

class UntypedStorage(object):
    def __init__(self, shape):
        self.storage = [None] * len(shape)
        self.shape = shape

    def getlength(self):
        return len(self.shape)

    def getshape(self):
        return self.shape

    def _typed_getset(char, cls):
        def getter(self, idx):
            assert self.shape[idx] == char
            v = self.storage[idx]
            assert isinstance(v, cls)
            return v
        def setter(self, idx, v):
            assert self.shape[idx] == char
            assert isinstance(v, cls)
            self.storage[idx] = v
        return getter, setter

    getint, setint = _typed_getset(INT, int)
    getbool, setbool = _typed_getset(BOOL, bool)
    getfloat, setfloat = _typed_getset(FLOAT, float)
    getstr, setstr = _typed_getset(STRING, str)

    def getinstance(self, idx, cls):
        obj = self.storage[idx]
        assert self.shape[idx] == INSTANCE
        assert isinstance(obj, cls)
        return obj

    def setinstance(self, idx, obj):
        assert self.shape[idx] == INSTANCE
        self.storage[idx] = obj


class UntypedStorageEntry(ExtRegistryEntry):
    _about_ = UntypedStorage

    def compute_result_annotation(self, s_shape):
        assert annmodel.SomeString().contains(s_shape)
        return SomeUntypedStorage()

    def specialize_call(self, hop):
        return hop.r_result.rtyper_new(hop)

class UntypedStoragePrebuiltEntry(ExtRegistryEntry):
    _type_ = UntypedStorage

    def compute_annotation(self):
        return SomeUntypedStorage()

class SomeUntypedStorage(annmodel.SomeObject):
    def _check_idx(self, s_idx):
        assert annmodel.SomeInteger().contains(s_idx)

    def rtyper_makerepr(self, rtyper):
        return UntypedStorageRepr(rtyper)

    def method_getlength(self):
        return annmodel.SomeInteger(nonneg=True)

    def method_getshape(self):
        return annmodel.SomeString(can_be_None=False)

    def method_getint(self, s_idx):
        self._check_idx(s_idx)
        return annmodel.SomeInteger()

    def method_setint(self, s_idx, s_v):
        self._check_idx(s_idx)
        assert annmodel.SomeInteger().contains(s_v)

    def method_getbool(self, s_idx):
        self._check_idx(s_idx)
        return annmodel.SomeBool()

    def method_setbool(self, s_idx, s_v):
        self._check_idx(s_idx)
        assert annmodel.SomeBool().contains(s_v)

    def method_getfloat(self, s_idx):
        self._check_idx(s_idx)
        return annmodel.SomeFloat()

    def method_setfloat(self, s_idx, s_f):
        self._check_idx(s_idx)
        assert annmodel.SomeFloat().contains(s_f)

    def method_getinstance(self, s_idx, s_cls):
        self._check_idx(s_idx)
        assert isinstance(s_cls, annmodel.SomePBC)
        bookkeeper = getbookkeeper()
        classdef = bookkeeper.getuniqueclassdef(s_cls.const)
        return annmodel.SomeInstance(classdef, can_be_None=True)

    def method_setinstance(self, s_idx, s_obj):
        self._check_idx(s_idx)
        assert isinstance(s_obj, annmodel.SomeInstance)

    def method_getstr(self, s_idx):
        self._check_idx(s_idx)
        return annmodel.SomeString()

    def method_setstr(self, s_idx, s_s):
        self._check_idx(s_idx)
        assert annmodel.SomeString().contains(s_s)


class __extend__(pairtype(SomeUntypedStorage, SomeUntypedStorage)):
    def union((self, other)):
        return SomeUntypedStorage()



UNTYPEDSTORAGE = lltype.GcStruct("untypedstorage",
    ("shape", lltype.Ptr(STR)),
    ("data", lltype.Array(llmemory.Address)),
    rtti=True,
)


CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                  llmemory.Address)
def trace_untypedstorage(obj_addr, prev):
    # XXX: This has O(n**2) complexity because of the below loop, if we could
    # do more arithmetic ops on addresses then it could be O(n).
    shape_addr = obj_addr + llmemory.offsetof(UNTYPEDSTORAGE, "shape")
    # prev == NULL means it's the first item, shape is always a GC pointer,
    # return it first
    if not prev:
        return shape_addr
    shape = shape_addr.address[0]
    # Find the length of the shape, which is also the length of data.
    length_offset = (llmemory.offsetof(STR, "chars") +
        llmemory.arraylengthoffset(STR.chars))
    length = (shape + length_offset).signed[0]

    # seen_prev indicates whether our loop has gone past the "prev" addr.
    seen_prev = prev == shape_addr
    i = 0
    while i < length:
        # This a pointer to the i-th item in data. (&obj_adr->data[i])
        data_ptr = (obj_addr + llmemory.offsetof(UNTYPEDSTORAGE, "data") +
            llmemory.itemoffsetof(UNTYPEDSTORAGE.data, 0) +
            llmemory.sizeof(UNTYPEDSTORAGE.data.OF) * i)

        # Check to see if we have gotten past the previous value, if we
        # haven't, check if we're there now.
        if not seen_prev:
            if data_ptr == prev:
                seen_prev = True
            i += 1
            continue

        # Find the i-th char in shape.
        char = (shape + llmemory.offsetof(STR, "chars") +
                llmemory.itemoffsetof(STR.chars, 0) +
                (llmemory.sizeof(STR.chars.OF) * i)).char[0]
        # If it's an instance or string then we've found a GC pointer.
        if char == INSTANCE or char == STRING:
            return data_ptr
        i += 1
    # If we've gotten to here, there are no GC-pointers left, return NULL to
    # exit out.
    return llmemory.NULL
trace_untypedstorage_ptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), trace_untypedstorage)

class UntypedStorageRepr(Repr):
    lowleveltype = lltype.Ptr(UNTYPEDSTORAGE)
    lltype.attachRuntimeTypeInfo(lowleveltype.TO, customtraceptr=trace_untypedstorage_ptr)

    def __init__(self, rtyper):
        self.rtyper = rtyper

    def _read_index(self, hop):
        v_arr = hop.inputarg(self, arg=0)
        v_idx = hop.inputarg(lltype.Signed, arg=1)
        c_name = hop.inputconst(lltype.Void, "data")
        hop.exception_cannot_occur()
        return hop.genop("getinteriorfield", [v_arr, c_name, v_idx],
                         resulttype=llmemory.Address)

    def _write_index(self, hop, v_value):
        v_arr = hop.inputarg(self, arg=0)
        v_idx = hop.inputarg(lltype.Signed, arg=1)
        hop.exception_cannot_occur()
        c_name = hop.inputconst(lltype.Void, "data")
        hop.genop("setinteriorfield", [v_arr, c_name, v_idx, v_value])

    def _write_index_gc(self, hop, v_value):
        v_arr = hop.inputarg(self, arg=0)
        hop.genop("gc_writebarrier", [v_value, v_arr])
        v_addr = hop.genop("cast_ptr_to_adr", [v_value],
                           resulttype=llmemory.Address)

        self._write_index(hop, v_addr)

    def convert_const(self, value):
        storage = self.ll_new(llstr(value.shape))
        for idx, (char, obj) in enumerate(zip(value.shape, value.storage)):
            if char == INT:
                storage.data[idx] = rffi.cast(llmemory.Address, obj)
            elif char == INSTANCE:
                bk = self.rtyper.annotator.bookkeeper
                classdef = bk.getuniqueclassdef(type(obj))
                instancerepr = getinstancerepr(self.rtyper, classdef)
                ptr = instancerepr.convert_const(obj)
                storage.data[idx] = llmemory.cast_ptr_to_adr(ptr)
        return storage

    def rtyper_new(self, hop):
        [v_shape] = hop.inputargs(string_repr)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_new, v_shape)

    def rtype_method_getlength(self, hop):
        [v_arr] = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_getlength, v_arr)

    def rtype_method_getshape(self, hop):
        [v_arr] = hop.inputargs(self)
        hop.exception_cannot_occur()
        c_name = hop.inputconst(lltype.Void, "shape")
        return hop.genop("getfield", [v_arr, c_name], resulttype=string_repr)

    def rtype_method_getint(self, hop):
        v_addr = self._read_index(hop)
        return hop.genop("force_cast", [v_addr], resulttype=lltype.Signed)

    def rtype_method_setint(self, hop):
        v_value = hop.inputarg(lltype.Signed, arg=2)
        v_addr = hop.genop("force_cast", [v_value], resulttype=llmemory.Address)
        self._write_index(hop, v_addr)

    def rtype_method_getbool(self, hop):
        v_addr = self._read_index(hop)
        return hop.genop("force_cast", [v_addr], resulttype=lltype.Bool)

    def rtype_method_setbool(self, hop):
        v_value = hop.inputarg(lltype.Bool, arg=2)
        v_addr = hop.genop("force_cast", [v_value], resulttype=llmemory.Address)
        self._write_index(hop, v_addr)

    def rtype_method_getfloat(self, hop):
        v_value = self._read_index(hop)
        return hop.genop("cast_adr_to_float", [v_value], resulttype=lltype.Float)

    def rtype_method_setfloat(self, hop):
        v_value = hop.inputarg(lltype.Float, arg=2)

        v_addr = hop.genop("cast_float_to_adr", [v_value], resulttype=llmemory.Address)
        self._write_index(hop, v_addr)

    def rtype_method_getinstance(self, hop):
        v_addr = self._read_index(hop)
        return hop.genop("cast_adr_to_ptr", [v_addr], resulttype=hop.r_result.lowleveltype)

    def rtype_method_setinstance(self, hop):
        v_instance = hop.inputarg(hop.args_r[2], arg=2)

        self._write_index_gc(hop, v_instance)

    def rtype_method_getstr(self, hop):
        v_addr = self._read_index(hop)
        return hop.genop("cast_adr_to_ptr", [v_addr], resulttype=string_repr)

    def rtype_method_setstr(self, hop):
        v_value = hop.inputarg(string_repr, arg=2)

        self._write_index_gc(hop, v_value)

    @classmethod
    def ll_new(cls, shape):
        obj = lltype.malloc(cls.lowleveltype.TO, len(shape.chars))
        obj.shape = shape
        return obj

    @classmethod
    def ll_getlength(cls, arr):
        return len(arr.shape.chars)
