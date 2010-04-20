from pypy.jit.codewriter.assembler import Assembler
from pypy.jit.codewriter.flatten import SSARepr, Label, TLabel, Register
from pypy.objspace.flow.model import Constant
from pypy.jit.metainterp.history import ConstInt


def test_assemble_simple():
    ssarepr = SSARepr("test")
    i0, i1, i2 = Register(0), Register(1), Register(2)
    ssarepr.insns = [
        ('int_add', i0, i1, i2),
        ('int_return', i2),
        ]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr)
    assert jitcode.code == ("\x00\x00\x01\x02"
                            "\x01\x02")
    assert assembler.insns == {'int_add/iii': 0,
                               'int_return/i': 1}

def test_assemble_consts():
    ssarepr = SSARepr("test")
    ssarepr.insns = [
        ('int_return', Register(13)),
        ('int_return', Constant(18)),
        ('int_return', Constant(-4)),
        ('int_return', Constant(128)),
        ('int_return', Constant(-129)),
        ]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr)
    assert jitcode.code == ("\x00\x0D"
                            "\x01\x12"   # use int_return/c for one-byte consts
                            "\x01\xFC"
                            "\x00\xFF"   # use int_return/i for larger consts
                            "\x00\xFE")
    assert assembler.insns == {'int_return/i': 0,
                               'int_return/c': 1}
    assert jitcode.constants == [ConstInt(-129), ConstInt(128)]

def test_assemble_loop():
    ssarepr = SSARepr("test")
    i0, i1 = Register(0x16), Register(0x17)
    ssarepr.insns = [
        (Label('L1'),),
        ('goto_if_not_int_gt', TLabel('L2'), i0, Constant(4)),
        ('int_add', i1, i0, i1),
        ('int_sub', i0, Constant(1), i0),
        ('goto', TLabel('L1')),
        (Label('L2'),),
        ('int_return', i1),
        ]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr)
    assert jitcode.code == ("\x00\x10\x00\x16\x04"
                            "\x01\x17\x16\x17"
                            "\x02\x16\x01\x16"
                            "\x03\x00\x00"
                            "\x04\x17")
    assert assembler.insns == {'goto_if_not_int_gt/Lic': 0,
                               'int_add/iii': 1,
                               'int_sub/ici': 2,
                               'goto/L': 3,
                               'int_return/i': 4}
