import random
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.jit.codewriter.jitter import Transformer
from pypy.jit.metainterp.history import getkind
from pypy.rpython.lltypesystem import lltype, rclass, rstr
from pypy.translator.unsimplify import varoftype

class FakeCPU:
    def calldescrof(self, FUNC, ARGS, RESULT):
        return ('calldescr', FUNC, ARGS, RESULT)
    def fielddescrof(self, STRUCT, name):
        return ('fielddescr', STRUCT, name)

class FakeLink:
    args = []

def test_optimize_goto_if_not():
    v1 = Variable()
    v2 = Variable()
    v3 = Variable(); v3.concretetype = lltype.Bool
    sp1 = SpaceOperation('foobar', [], None)
    sp2 = SpaceOperation('foobaz', [], None)
    block = Block([v1, v2])
    block.operations = [sp1, SpaceOperation('int_gt', [v1, v2], v3), sp2]
    block.exitswitch = v3
    block.exits = exits = [FakeLink(), FakeLink()]
    res = Transformer().optimize_goto_if_not(block)
    assert res == True
    assert block.operations == [sp1, sp2]
    assert block.exitswitch == ('int_gt', v1, v2)
    assert block.exits == exits

def test_optimize_goto_if_not__incoming():
    v1 = Variable(); v1.concretetype = lltype.Bool
    block = Block([v1])
    block.exitswitch = v1
    block.exits = [FakeLink(), FakeLink()]
    assert not Transformer().optimize_goto_if_not(block)

def test_optimize_goto_if_not__exit():
    v1 = Variable()
    v2 = Variable()
    v3 = Variable(); v3.concretetype = lltype.Bool
    block = Block([v1, v2])
    block.operations = [SpaceOperation('int_gt', [v1, v2], v3)]
    block.exitswitch = v3
    block.exits = [FakeLink(), FakeLink()]
    block.exits[1].args = [v3]
    assert not Transformer().optimize_goto_if_not(block)

def test_optimize_goto_if_not__unknownop():
    v3 = Variable(); v3.concretetype = lltype.Bool
    block = Block([])
    block.operations = [SpaceOperation('foobar', [], v3)]
    block.exitswitch = v3
    block.exits = [FakeLink(), FakeLink()]
    assert not Transformer().optimize_goto_if_not(block)

def test_residual_call():
    for RESTYPE in [lltype.Signed, rclass.OBJECTPTR,
                    lltype.Float, lltype.Void]:
      for with_void in [False, True]:
        for with_i in [False, True]:
          for with_r in [False, True]:
            for with_f in [False, True]:
              ARGS = []
              if with_void: ARGS += [lltype.Void, lltype.Void]
              if with_i: ARGS += [lltype.Signed, lltype.Char]
              if with_r: ARGS += [rclass.OBJECTPTR, lltype.Ptr(rstr.STR)]
              if with_f: ARGS += [lltype.Float, lltype.Float]
              random.shuffle(ARGS)
              if with_f: expectedkind = 'irf'   # all kinds
              elif with_i: expectedkind = 'ir'  # integers and references
              else: expectedkind = 'r'          # only references
              yield residual_call_test, ARGS, RESTYPE, expectedkind

def get_direct_call_op(argtypes, restype):
    FUNC = lltype.FuncType(argtypes, restype)
    fnptr = lltype.functionptr(FUNC, "g")    # no graph
    c_fnptr = Constant(fnptr, concretetype=lltype.typeOf(fnptr))
    vars = [varoftype(TYPE) for TYPE in argtypes]
    v_result = varoftype(restype)
    op = SpaceOperation('direct_call', [c_fnptr] + vars, v_result)
    return op

def residual_call_test(argtypes, restype, expectedkind):
    op = get_direct_call_op(argtypes, restype)
    op1 = Transformer(FakeCPU()).rewrite_operation(op)
    reskind = getkind(restype)[0]
    assert op1.opname == 'residual_call_%s_%s' % (expectedkind, reskind)
    assert op1.result == op.result
    assert op1.args[0] == op.args[0]
    FUNC = op.args[0].concretetype.TO
    NONVOIDARGS = tuple([ARG for ARG in FUNC.ARGS if ARG != lltype.Void])
    assert op1.args[1] == ('calldescr', FUNC, NONVOIDARGS, FUNC.RESULT)
    assert len(op1.args) == 2 + len(expectedkind)
    for sublist, kind1 in zip(op1.args[2:], expectedkind):
        assert sublist.kind.startswith(kind1)
        assert list(sublist) == [v for v in op.args[1:]
                                 if getkind(v.concretetype) == sublist.kind]
    for v in op.args[1:]:
        kind = getkind(v.concretetype)
        assert kind == 'void' or kind[0] in expectedkind

def test_getfield():
    # XXX a more compact encoding would be possible, something along
    # the lines of  getfield_gc_r %r0, $offset, %r1
    # which would not need a Descr at all.
    S1 = lltype.Struct('S1')
    S2 = lltype.GcStruct('S2')
    S  = lltype.GcStruct('S', ('int', lltype.Signed),
                              ('ps1', lltype.Ptr(S1)),
                              ('ps2', lltype.Ptr(S2)),
                              ('flt', lltype.Float),
                              ('boo', lltype.Bool),
                              ('chr', lltype.Char),
                              ('unc', lltype.UniChar))
    for name, suffix in [('int', 'i'),
                         ('ps1', 'i'),
                         ('ps2', 'r'),
                         ('flt', 'f'),
                         ('boo', 'c'),
                         ('chr', 'c'),
                         ('unc', 'u')]:
        v_parent = varoftype(lltype.Ptr(S))
        c_name = Constant(name, lltype.Void)
        v_result = varoftype(getattr(S, name))
        op = SpaceOperation('getfield', [v_parent, c_name], v_result)
        op1 = Transformer(FakeCPU()).rewrite_operation(op)
        assert op1.opname == 'getfield_gc_' + suffix
        fielddescr = ('fielddescr', S, name)
        assert op1.args == [v_parent, fielddescr]
        assert op1.result == v_result
