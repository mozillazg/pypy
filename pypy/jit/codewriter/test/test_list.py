from pypy.rpython.lltypesystem import lltype
from pypy.translator.unsimplify import varoftype
from pypy.objspace.flow.model import Constant

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
    oplist = tr._handle_list_call(oopspec_name, args, v_result)
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
                             Constant(1, lltype.Signed)], FIXEDLIST,
                 None)
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             varoftype(lltype.Signed)], FIXEDLIST,
                 None)
