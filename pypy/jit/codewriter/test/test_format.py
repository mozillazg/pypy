import py
from pypy.objspace.flow.model import Constant
from pypy.jit.codewriter.format import format_assembler
from pypy.jit.codewriter.flatten import Label, TLabel, SSARepr, Register
from pypy.jit.codewriter.flatten import ListOfKind
from pypy.jit.metainterp.history import AbstractDescr
from pypy.rpython.lltypesystem import lltype


def test_format_assembler_simple():
    ssarepr = SSARepr("test")
    i0, i1, i2 = Register('int', 0), Register('int', 1), Register('int', 2)
    ssarepr.insns = [
        ('int_add', i0, i1, i2),
        ('int_return', i2),
        ]
    asm = format_assembler(ssarepr)
    expected = """
        int_add %i0, %i1, %i2
        int_return %i2
    """
    assert asm == str(py.code.Source(expected)).strip() + '\n'

def test_format_assembler_float():
    ssarepr = SSARepr("test")
    i1, r2, f3 = Register('int', 1), Register('ref', 2), Register('float', 3)
    ssarepr.insns = [
        ('foobar', i1, r2, f3),
        ]
    asm = format_assembler(ssarepr)
    expected = """
        foobar %i1, %r2, %f3
    """
    assert asm == str(py.code.Source(expected)).strip() + '\n'

def test_format_assembler_loop():
    ssarepr = SSARepr("test")
    i0, i1 = Register('int', 0), Register('int', 1)
    ssarepr.insns = [
        (Label('L1'),),
        ('goto_if_not_int_gt', TLabel('L2'), i0, Constant(0)),
        ('int_add', i1, i0, i1),
        ('int_sub', i0, Constant(1), i0),
        ('goto', TLabel('L1')),
        (Label('L2'),),
        ('int_return', i1),
        ]
    asm = format_assembler(ssarepr)
    expected = """
        L1:
        goto_if_not_int_gt L2, %i0, $0
        int_add %i1, %i0, %i1
        int_sub %i0, $1, %i0
        goto L1
        L2:
        int_return %i1
    """
    assert asm == str(py.code.Source(expected)).strip() + '\n'

def test_format_assembler_list():
    ssarepr = SSARepr("test")
    i0, i1 = Register('int', 0), Register('int', 1)
    ssarepr.insns = [
        ('foobar', ListOfKind('int', [i0, Constant(123, lltype.Signed), i1])),
        ]
    asm = format_assembler(ssarepr)
    expected = """
        foobar i[%i0, $123, %i1]
    """
    assert asm == str(py.code.Source(expected)).strip() + '\n'

def test_format_assembler_descr():
    class FooDescr(AbstractDescr):
        def __repr__(self):
            return 'hi_there!'
    ssarepr = SSARepr("test")
    ssarepr.insns = [
        ('foobar', FooDescr()),
        ]
    asm = format_assembler(ssarepr)
    expected = """
        foobar hi_there!
    """
    assert asm == str(py.code.Source(expected)).strip() + '\n'
