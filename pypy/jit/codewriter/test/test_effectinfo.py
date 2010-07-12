from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import gengraph
from pypy.jit.codewriter.effectinfo import effectinfo_from_writeanalyze
from pypy.jit.codewriter.effectinfo import VirtualizableAnalyzer

class FakeCPU:
    def fielddescrof(self, T, fieldname):
        return ('fielddescr', T, fieldname)
    def arraydescrof(self, A):
        return ('arraydescr', A)

def test_include_read_field():
    S = lltype.GcStruct("S", ("a", lltype.Signed))
    effects = frozenset([("readstruct", lltype.Ptr(S), "a")])
    effectinfo = effectinfo_from_writeanalyze(effects, FakeCPU())
    assert list(effectinfo.readonly_descrs_fields) == [('fielddescr', S, "a")]
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_include_write_field():
    S = lltype.GcStruct("S", ("a", lltype.Signed))
    effects = frozenset([("struct", lltype.Ptr(S), "a")])
    effectinfo = effectinfo_from_writeanalyze(effects, FakeCPU())
    assert list(effectinfo.write_descrs_fields) == [('fielddescr', S, "a")]
    assert not effectinfo.readonly_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_include_write_array():
    A = lltype.GcArray(lltype.Signed)
    effects = frozenset([("array", lltype.Ptr(A))])
    effectinfo = effectinfo_from_writeanalyze(effects, FakeCPU())
    assert not effectinfo.readonly_descrs_fields
    assert not effectinfo.write_descrs_fields
    assert list(effectinfo.write_descrs_arrays) == [('arraydescr', A)]

def test_dont_include_read_and_write_field():
    S = lltype.GcStruct("S", ("a", lltype.Signed))
    effects = frozenset([("readstruct", lltype.Ptr(S), "a"),
                         ("struct", lltype.Ptr(S), "a")])
    effectinfo = effectinfo_from_writeanalyze(effects, FakeCPU())
    assert not effectinfo.readonly_descrs_fields
    assert list(effectinfo.write_descrs_fields) == [('fielddescr', S, "a")]
    assert not effectinfo.write_descrs_arrays


def test_filter_out_typeptr():
    effects = frozenset([("struct", lltype.Ptr(OBJECT), "typeptr")])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.readonly_descrs_fields
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_array_of_void():
    effects = frozenset([("array", lltype.Ptr(lltype.GcArray(lltype.Void)))])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.readonly_descrs_fields
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_struct_with_void():
    effects = frozenset([("struct", lltype.Ptr(lltype.GcStruct("x", ("a", lltype.Void))), "a")])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.readonly_descrs_fields
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_ooarray_of_void():
    effects = frozenset([("array", ootype.Array(ootype.Void))])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.readonly_descrs_fields
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays

def test_filter_out_instance_with_void():
    effects = frozenset([("struct", ootype.Instance("x", ootype.ROOT, {"a": ootype.Void}), "a")])
    effectinfo = effectinfo_from_writeanalyze(effects, None)
    assert not effectinfo.readonly_descrs_fields
    assert not effectinfo.write_descrs_fields
    assert not effectinfo.write_descrs_arrays


def test_external_calls():
    C_METHPTRGETTER = lltype.FuncType([lltype.Signed], lltype.Signed)
    c_get_methptr_getter = rffi.llexternal(
        "cppyy_get_methptr_getter",
        [lltype.Signed], lltype.Ptr(C_METHPTRGETTER))
    #
    def f(handle):
        methgetter = c_get_methptr_getter(handle)
        return methgetter(123)
    t, _, graph = gengraph(f, [int])
    #
    va = VirtualizableAnalyzer(t)
    result = va.analyze_direct_call(graph)
    assert result is False
