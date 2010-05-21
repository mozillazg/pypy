from pypy.rpython.lltypesystem import lltype
from pypy.translator.unsimplify import varoftype
from pypy.objspace.flow.model import Constant, SpaceOperation

from pypy.jit.codewriter.jtransform import Transformer
from pypy.jit.codewriter.flatten import GraphFlattener
from pypy.jit.codewriter.format import assert_format
from pypy.jit.codewriter.test.test_flatten import fake_regallocs
from pypy.jit.metainterp.history import AbstractDescr

# ____________________________________________________________

FIXEDLIST = lltype.Ptr(lltype.GcArray(lltype.Signed))

class FakeCPU:
    class arraydescrof(AbstractDescr):
        def __init__(self, ARRAY):
            self.ARRAY = ARRAY
        def __repr__(self):
            return '<ArrayDescr>'

def builtin_test(oopspec_name, args, RESTYPE, expected):
    v_result = varoftype(RESTYPE)
    tr = Transformer(FakeCPU())
    if '/' in oopspec_name:
        oopspec_name, property = oopspec_name.split('/')
        def force_flags(op):
            if property == 'NONNEG':   return True, False
            if property == 'NEG':      return False, False
            if property == 'CANRAISE': return False, True
            raise ValueError(property)
        tr._get_list_nonneg_canraise_flags = force_flags
    op = SpaceOperation('direct_call', [Constant("myfunc")] + args,
                        v_result)
    oplist = tr._handle_list_call(op, oopspec_name, args)
    if expected is None:
        assert oplist is None
    else:
        assert oplist is not None
        flattener = GraphFlattener(None, fake_regallocs())
        if not isinstance(oplist, list):
            oplist = [oplist]
        for op1 in oplist:
            flattener.serialize_op(op1)
        assert_format(flattener.ssarepr, expected)

# ____________________________________________________________

def test_newlist():
    builtin_test('newlist', [], FIXEDLIST,
                 """new_array <ArrayDescr>, $0 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed)], FIXEDLIST,
                 """new_array <ArrayDescr>, $5 -> %r0""")
    builtin_test('newlist', [varoftype(lltype.Signed)], FIXEDLIST,
                 """new_array <ArrayDescr>, %i0 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             Constant(0, lltype.Signed)], FIXEDLIST,
                 """new_array <ArrayDescr>, $5 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             Constant(1, lltype.Signed)], FIXEDLIST, None)
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             varoftype(lltype.Signed)], FIXEDLIST, None)

def test_fixed_ll_arraycopy():
    xxx

def test_fixed_getitem():
    builtin_test('list.getitem/NONNEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     getarrayitem_gc_i %r0, <ArrayDescr>, %i0 -> %i1
                 """)
    builtin_test('list.getitem/NEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     check_neg_index %r0, <ArrayDescr>, %i0 -> %i1
                     getarrayitem_gc_i %r0, <ArrayDescr>, %i1 -> %i2
                 """)
    builtin_test('list.getitem/CANRAISE',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, None)

def test_fixed_getitem_foldable():
    builtin_test('list.getitem_foldable/NONNEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     getarrayitem_gc_pure_i %r0, <ArrayDescr>, %i0 -> %i1
                 """)
    builtin_test('list.getitem_foldable/NEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     check_neg_index %r0, <ArrayDescr>, %i0 -> %i1
                     getarrayitem_gc_pure_i %r0, <ArrayDescr>, %i1 -> %i2
                 """)
    builtin_test('list.getitem_foldable/CANRAISE',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, None)

def test_fixed_setitem():
    builtin_test('list.setitem/NONNEG', [varoftype(FIXEDLIST),
                                         varoftype(lltype.Signed),
                                         varoftype(lltype.Signed)],
                 lltype.Void, """
                     setarrayitem_gc_i %r0, <ArrayDescr>, %i0, %i1
                 """)
    builtin_test('list.setitem/NEG', [varoftype(FIXEDLIST),
                                      varoftype(lltype.Signed),
                                      varoftype(lltype.Signed)],
                 lltype.Void, """
                     check_neg_index %r0, <ArrayDescr>, %i0 -> %i1
                     setarrayitem_gc_i %r0, <ArrayDescr>, %i1, %i2
                 """)
    builtin_test('list.setitem/CANRAISE', [varoftype(FIXEDLIST),
                                           varoftype(lltype.Signed),
                                           varoftype(lltype.Signed)],
                 lltype.Void, None)

def test_fixed_len():
    builtin_test('list.len', [varoftype(FIXEDLIST)], lltype.Signed,
                 """arraylen_gc %r0, <ArrayDescr> -> %i0""")

def test_fixed_len_foldable():
    builtin_test('list.len_foldable', [varoftype(FIXEDLIST)], lltype.Signed,
                 """arraylen_gc %r0, <ArrayDescr> -> %i0""")

def test_resizable_newlist():
    xxx

def test_resizable_getitem():
    xxx

def test_resizable_setitem():
    xxx

def test_resizable_len():
    xxx

def test_resizable_unsupportedop():
    builtin_test('list.foobar', [varoftype(VARLIST)], lltype.Signed, None)
