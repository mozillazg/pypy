from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.jit.codewriter import jitter
from pypy.rpython.lltypesystem import lltype

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
    res = jitter.optimize_goto_if_not(block)
    assert res == True
    assert block.operations == [sp1, sp2]
    assert block.exitswitch == ('int_gt', v1, v2)
    assert block.exits == exits

def test_optimize_goto_if_not__incoming():
    v1 = Variable(); v1.concretetype = lltype.Bool
    block = Block([v1])
    block.exitswitch = v1
    block.exits = [FakeLink(), FakeLink()]
    assert not jitter.optimize_goto_if_not(block)

def test_optimize_goto_if_not__exit():
    v1 = Variable()
    v2 = Variable()
    v3 = Variable(); v3.concretetype = lltype.Bool
    block = Block([v1, v2])
    block.operations = [SpaceOperation('int_gt', [v1, v2], v3)]
    block.exitswitch = v3
    block.exits = [FakeLink(), FakeLink()]
    block.exits[1].args = [v3]
    assert not jitter.optimize_goto_if_not(block)

def test_optimize_goto_if_not__unknownop():
    v3 = Variable(); v3.concretetype = lltype.Bool
    block = Block([])
    block.operations = [SpaceOperation('foobar', [], v3)]
    block.exitswitch = v3
    block.exits = [FakeLink(), FakeLink()]
    assert not jitter.optimize_goto_if_not(block)
