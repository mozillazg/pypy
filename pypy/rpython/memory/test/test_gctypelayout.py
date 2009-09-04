from pypy.rpython.memory.gctypelayout import TypeLayoutBuilder, GCData
from pypy.rpython.memory.gctypelayout import offsets_to_gc_pointers
from pypy.rpython.lltypesystem import lltype, llmemory

def getname(T):
    try:
        return "field:" + T._name
    except:
        return "field:" + T.__name__

S = lltype.Struct('S', ('s', lltype.Signed), ('char', lltype.Char))
GC_S = lltype.GcStruct('GC_S', ('S', S))

A = lltype.Array(S)
GC_A = lltype.GcArray(S)

S2 = lltype.Struct('SPTRS',
                   *[(getname(TYPE), lltype.Ptr(TYPE)) for TYPE in (GC_S, GC_A)])  
GC_S2 = lltype.GcStruct('GC_S2', ('S2', S2))

A2 = lltype.Array(S2)
GC_A2 = lltype.GcArray(S2)

l = [(getname(TYPE), lltype.Ptr(TYPE)) for TYPE in (GC_S, GC_A)]
l.append(('vararray', A2))

GC_S3 = lltype.GcStruct('GC_S3', *l)

def test_struct():
    for T, c in [(GC_S, 0), (GC_S2, 2), (GC_A, 0), (GC_A2, 0), (GC_S3, 2)]:
        assert len(offsets_to_gc_pointers(T)) == c

def test_layout_builder():
    # XXX a very minimal test
    layoutbuilder = TypeLayoutBuilder()
    for T1, T2 in [(GC_A, GC_S), (GC_A2, GC_S2), (GC_S3, GC_S2)]:
        tid1 = layoutbuilder.get_type_id(T1)
        tid2 = layoutbuilder.get_type_id(T2)
        gcdata = GCData(layoutbuilder.type_info_list)
        lst1 = gcdata.q_varsize_offsets_to_gcpointers_in_var_part(tid1)
        lst2 = gcdata.q_offsets_to_gc_pointers(tid2)
        assert len(lst1) == len(lst2)

def test_weakarray():
    OBJ = lltype.GcStruct('some_object')
    S = lltype.Struct('weakstruct',
                      ('foo', lltype.Ptr(OBJ)),
                      ('bar', lltype.Ptr(OBJ)))
    A = lltype.GcArray(S, hints={'weakarray': 'bar'})
    layoutbuilder = TypeLayoutBuilder()
    tid = layoutbuilder.get_type_id(A)
    gcdata = GCData(layoutbuilder.type_info_list)
    assert gcdata.q_is_varsize(tid)
    assert gcdata.q_has_gcptr_in_varsize(tid)
    assert not gcdata.q_is_gcarrayofgcptr(tid)
    assert len(gcdata.q_offsets_to_gc_pointers(tid)) == 0
    assert len(gcdata.q_varsize_offsets_to_gcpointers_in_var_part(tid)) == 2
    weakofs = gcdata.q_weakpointer_offset(tid)
    assert isinstance(weakofs, llmemory.FieldOffset)
    assert weakofs.TYPE == S
    assert weakofs.fldname == 'bar'
