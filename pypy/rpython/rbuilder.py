
from pypy.annotation.model import SomeObject, SomeString, s_None,\
     SomeChar, SomeInteger, SomeUnicodeCodePoint, SomeUnicodeString
from pypy.rpython.rmodel import Repr
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype

class SomeStringBuilder(SomeObject):
    def __init__(self, init_size):
        self.init_size = init_size

    def method_append(self, s_str):
        assert isinstance(s_str, (SomeString, SomeChar))
        return s_None

    def method_append_slice(self, s_str, s_start, s_end):
        assert isinstance(s_str, SomeString)
        assert isinstance(s_start, SomeInteger)
        assert isinstance(s_end, SomeInteger)
        assert s_start.nonneg
        assert s_end.nonneg
        return s_None

    def method_append_multiple_char(self, s_char, s_times):
        assert isinstance(s_char, SomeChar)
        assert isinstance(s_times, SomeInteger)
        assert s_times.nonneg
        return s_None

    def method_build(self):
        return SomeString()
    
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rbuilder.stringbuilder_repr

class SomeUnicodeBuilder(SomeObject):
    def __init__(self, init_size):
        self.init_size = init_size
    
    def method_append(self, s_str):
        assert isinstance(s_str, (SomeUnicodeCodePoint, SomeUnicodeString))
        return s_None

    def method_append_slice(self, s_str, s_start, s_end):
        assert isinstance(s_str, SomeUnicodeString)
        assert isinstance(s_start, SomeInteger)
        assert isinstance(s_end, SomeInteger)
        assert s_start.nonneg
        assert s_end.nonneg
        return s_None

    def method_append_multiple_char(self, s_char, s_times):
        assert isinstance(s_char, SomeUnicodeCodePoint)
        assert isinstance(s_times, SomeInteger)
        assert s_times.nonneg
        return s_None

    def method_build(self):
        return SomeUnicodeString()
    
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rbuilder.unicodebuilder_repr

class AbstractStringBuilderRepr(Repr):
    def rtyper_new(self, hop):
        repr = hop.r_result
        if len(hop.args_v) == 0:
            v_arg = hop.inputconst(lltype.Signed, hop.s_result.init_size)
        else:
            v_arg = hop.inputarg(lltype.Signed, 0)
        return hop.gendirectcall(self.ll_new, v_arg)

    def rtype_method_append(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        if isinstance(hop.args_s[1], (SomeChar, SomeUnicodeCodePoint)):
            return hop.gendirectcall(self.ll_append_char, *vlist)
        return hop.gendirectcall(self.ll_append, *vlist)

    def rtype_method_append_slice(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        return hop.gendirectcall(self.ll_append_slice, *vlist)

    def rtype_method_append_multiple_char(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        return hop.gendirectcall(self.ll_append_multiple_char, *vlist)

    def rtype_method_build(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        return hop.gendirectcall(self.ll_build, *vlist)

