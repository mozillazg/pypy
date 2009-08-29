from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport import symbolic
from pypy.rlib.objectmodel import Symbolic


def test_get_size_descr():
    T = lltype.GcStruct('T')
    S = lltype.GcStruct('S', ('x', lltype.Char),
                             ('y', lltype.Ptr(T)))
    descr_s = get_size_descr(S, False)
    descr_t = get_size_descr(T, False)
    assert descr_s.size == symbolic.get_size(S, False)
    assert descr_t.size == symbolic.get_size(T, False)
    assert descr_s == get_size_descr(S, False)
    assert descr_s != get_size_descr(S, True)
    #
    descr_s = get_size_descr(S, True)
    assert isinstance(descr_s.size, Symbolic)


def test_get_field_descr():
    U = lltype.Struct('U')
    T = lltype.GcStruct('T')
    S = lltype.GcStruct('S', ('x', lltype.Char),
                             ('y', lltype.Ptr(T)),
                             ('z', lltype.Ptr(U)))
    assert getFieldDescrClass(lltype.Ptr(T)) is GcPtrFieldDescr
    assert getFieldDescrClass(lltype.Ptr(U)) is NonGcPtrFieldDescr
    cls = getFieldDescrClass(lltype.Char)
    assert cls != getFieldDescrClass(lltype.Signed)
    assert cls == getFieldDescrClass(lltype.Char)
    #
    assert get_field_descr(S, 'y', False) == get_field_descr(S, 'y', False)
    assert get_field_descr(S, 'y', False) != get_field_descr(S, 'y', True)
    for tsc in [False, True]:
        descr_x = get_field_descr(S, 'x', tsc)
        descr_y = get_field_descr(S, 'y', tsc)
        descr_z = get_field_descr(S, 'z', tsc)
        assert descr_x.__class__ is cls
        assert descr_y.__class__ is GcPtrFieldDescr
        assert descr_z.__class__ is NonGcPtrFieldDescr
        if not tsc:
            assert descr_x.offset < descr_y.offset < descr_z.offset
            assert descr_x.sort_key() < descr_y.sort_key() < descr_z.sort_key()
            assert descr_x.get_field_size(False) == rffi.sizeof(lltype.Char)
            assert descr_y.get_field_size(False) == rffi.sizeof(lltype.Ptr(T))
            assert descr_z.get_field_size(False) == rffi.sizeof(lltype.Ptr(U))
        else:
            assert isinstance(descr_x.offset, Symbolic)
            assert isinstance(descr_y.offset, Symbolic)
            assert isinstance(descr_z.offset, Symbolic)
            assert isinstance(descr_x.get_field_size(True), Symbolic)
            assert isinstance(descr_y.get_field_size(True), Symbolic)
            assert isinstance(descr_z.get_field_size(True), Symbolic)
        assert not descr_x.is_pointer_field()
        assert     descr_y.is_pointer_field()
        assert not descr_z.is_pointer_field()


def test_get_array_descr():
    U = lltype.Struct('U')
    T = lltype.GcStruct('T')
    A1 = lltype.GcArray(lltype.Char)
    A2 = lltype.GcArray(lltype.Ptr(T))
    A3 = lltype.GcArray(lltype.Ptr(U))
    assert getArrayDescrClass(A2) is GcPtrArrayDescr
    assert getArrayDescrClass(A3) is NonGcPtrArrayDescr
    cls = getArrayDescrClass(A1)
    assert cls != getArrayDescrClass(lltype.GcArray(lltype.Signed))
    assert cls == getArrayDescrClass(lltype.GcArray(lltype.Char))
    #
    descr1 = get_array_descr(A1)
    descr2 = get_array_descr(A2)
    descr3 = get_array_descr(A3)
    assert descr1.__class__ is cls
    assert descr2.__class__ is GcPtrArrayDescr
    assert descr3.__class__ is NonGcPtrArrayDescr
    assert descr1 == get_array_descr(lltype.GcArray(lltype.Char))
    assert not descr1.is_array_of_pointers()
    assert     descr2.is_array_of_pointers()
    assert not descr3.is_array_of_pointers()
    #
    WORD = rffi.sizeof(lltype.Signed)
    assert descr1.get_base_size(False) == WORD
    assert descr2.get_base_size(False) == WORD
    assert descr3.get_base_size(False) == WORD
    assert descr1.get_ofs_length(False) == 0
    assert descr2.get_ofs_length(False) == 0
    assert descr3.get_ofs_length(False) == 0
    assert descr1.get_item_size(False) == rffi.sizeof(lltype.Char)
    assert descr2.get_item_size(False) == rffi.sizeof(lltype.Ptr(T))
    assert descr3.get_item_size(False) == rffi.sizeof(lltype.Ptr(U))
    #
    assert isinstance(descr1.get_base_size(True), Symbolic)
    assert isinstance(descr2.get_base_size(True), Symbolic)
    assert isinstance(descr3.get_base_size(True), Symbolic)
    assert isinstance(descr1.get_ofs_length(True), Symbolic)
    assert isinstance(descr2.get_ofs_length(True), Symbolic)
    assert isinstance(descr3.get_ofs_length(True), Symbolic)
    assert isinstance(descr1.get_item_size(True), Symbolic)
    assert isinstance(descr2.get_item_size(True), Symbolic)
    assert isinstance(descr3.get_item_size(True), Symbolic)


def test_get_call_descr():
    cache = {}
    descr1 = get_call_descr([lltype.Char, lltype.Signed], lltype.Char, False,
                            cache)
    assert descr1.get_result_size(False) == rffi.sizeof(lltype.Char)
    assert not descr1.returns_a_pointer()
    assert descr1.arg_classes == [BoxInt, BoxInt]
    #
    T = lltype.GcStruct('T')
    descr2 = get_call_descr([lltype.Ptr(T)], lltype.Ptr(T), False, cache)
    assert descr2.get_result_size(False) == rffi.sizeof(lltype.Ptr(T))
    assert descr2.returns_a_pointer()
    assert descr2.arg_classes == [BoxPtr]
    #
    U = lltype.GcStruct('U', ('x', lltype.Signed))
    assert descr2 == get_call_descr([lltype.Ptr(U)], lltype.Ptr(U), False,
                                    cache)


def test_repr_of_descr():
    T = lltype.GcStruct('T')
    S = lltype.GcStruct('S', ('x', lltype.Char),
                             ('y', lltype.Ptr(T)),
                             ('z', lltype.Ptr(T)))
    descr1 = get_size_descr(S, False)
    s = symbolic.get_size(S, False)
    assert descr1.repr_of_descr() == '<SizeDescr %d>' % s
    #
    descr2 = get_field_descr(S, 'y', False)
    o, _ = symbolic.get_field_token(S, 'y', False)
    assert descr2.repr_of_descr() == '<GcPtrFieldDescr %d>' % o
    #
    descr2i = get_field_descr(S, 'x', False)
    o, _ = symbolic.get_field_token(S, 'x', False)
    assert descr2i.repr_of_descr() == '<CharFieldDescr %d>' % o
    #
    descr3 = get_array_descr(lltype.GcArray(lltype.Ptr(S)))
    assert descr3.repr_of_descr() == '<GcPtrArrayDescr>'
    #
    descr3i = get_array_descr(lltype.GcArray(lltype.Char))
    assert descr3i.repr_of_descr() == '<CharArrayDescr>'
    #
    cache = {}
    descr4 = get_call_descr([lltype.Char, lltype.Ptr(S)], lltype.Ptr(S),
                            False, cache)
    assert 'GcPtrCallDescr' in descr4.repr_of_descr()
    #
    descr4i = get_call_descr([lltype.Char, lltype.Ptr(S)], lltype.Char,
                             False, cache)
    assert 'IntCallDescr' in descr4i.repr_of_descr()
