"""
This module supports raw storage of arbitrary data (GC ptr, instance, float,
int) into a void *.  The creator of the UntypedStorage is responsible for
making sure that the shape string is cached correctly.
"""

from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.rpython.annlowlevel import hlstr, llstr, llhelper
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rpython.lltypesystem.rstr import STR, string_repr
from pypy.rpython.rmodel import Repr


INT = "i"
FLOAT = "f"
INSTANCE = "o"

class UntypedStorage(object):
    def __init__(self, shape):
        self.storage = [None] * len(shape)
        self.shape = shape

    def getlength(self):
        return len(self.shape)

    def getshape(self):
        return self.shape

    def getint(self, idx):
        assert self.shape[idx] == INT
        v = self.storage[idx]
        assert isinstance(v, int)
        return v

    def setint(self, idx, v):
        assert self.shape[idx] == INT
        assert isinstance(v, int)
        self.storage[idx] = v

    def getfloat(self, idx):
        assert self.shape[idx] == FLOAT
        v = self.storage[idx]
        assert isinstance(v, float)
        return v

    def setfloat(self, idx, f):
        assert self.shape[idx] == FLOAT
        assert isinstance(f, float)
        self.storage[idx] = f

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


class SomeUntypedStorage(annmodel.SomeObject):
    def _check_idx(self, s_idx):
        assert annmodel.SomeInteger().contains(s_idx)

    def rtyper_makerepr(self, rtyper):
        return UntypedStorageRepr()

    def method_getlength(self):
        return annmodel.SomeInteger()

    def method_getshape(self):
        return annmodel.SomeString(can_be_None=False)

    def method_getint(self, s_idx):
        self._check_idx(s_idx)
        return annmodel.SomeInteger()

    def method_setint(self, s_idx, s_v):
        self._check_idx(s_idx)
        assert annmodel.SomeInteger().contains(s_v)

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
    if not prev:
        return shape_addr
    shape = shape_addr.address[0]
    length_offset = (llmemory.offsetof(STR, "chars") +
        llmemory.arraylengthoffset(STR.chars))
    length = (shape + length_offset).signed[0]

    seen_prev = prev == shape_addr
    i = 0
    while i < length:
        data_ptr = (obj_addr + llmemory.offsetof(UNTYPEDSTORAGE, "data") +
            llmemory.itemoffsetof(UNTYPEDSTORAGE.data, 0) +
            llmemory.sizeof(UNTYPEDSTORAGE.data.OF) * i)

        if not seen_prev:
            if data_ptr == prev:
                seen_prev = True
            i += 1
            continue

        char = (shape + llmemory.offsetof(STR, "chars") +
                llmemory.itemoffsetof(STR.chars, 0) +
                (llmemory.sizeof(STR.chars.OF) * i)).char[0]
        if char == INSTANCE:
            return data_ptr
        i += 1
    return llmemory.NULL
trace_untypedstorage_ptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), trace_untypedstorage)

class UntypedStorageRepr(Repr):
    lowleveltype = lltype.Ptr(UNTYPEDSTORAGE)
    lltype.attachRuntimeTypeInfo(lowleveltype.TO, customtraceptr=trace_untypedstorage_ptr)

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
        v_arr = hop.inputarg(self, arg=0)
        v_instance = hop.inputarg(hop.args_r[2], arg=2)
        hop.genop("gc_writebarrier", [v_instance, v_arr])

        v_addr = hop.genop("cast_ptr_to_adr", [v_instance],
                           resulttype=llmemory.Address)
        self._write_index(hop, v_addr)

    @classmethod
    def ll_new(cls, shape):
        obj = lltype.malloc(cls.lowleveltype.TO, len(shape.chars))
        obj.shape = shape
        return obj

    @classmethod
    def ll_getlength(cls, arr):
        return len(arr.shape.chars)
