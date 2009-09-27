
from pypy.jit.metainterp.history import BoxInt, ConstInt
from pypy.jit.backend.llsupport.regalloc import RegisterManager

def boxes(*values):
    return [BoxInt(v) for v in values]

class FakeReg(object):
    pass

r0, r1, r2, r3 = [FakeReg() for _ in range(4)]
regs = [r0, r1, r2, r3]

class TestRegalloc(object):
    def test_freeing_vars(self):
        b0, b1, b2 = boxes(0, 0, 0)
        longevity = {b0: (0, 1), b1: (0, 2), b2: (0, 2)}
        rm = RegisterManager(regs, longevity)
        for b in b0, b1, b2:
            rm.try_allocate_reg(b)
        rm._check_invariants()
        assert len(rm.free_regs) == 1
        assert len(rm.reg_bindings) == 3
        rm.possibly_free_vars([b0, b1, b2])
        assert len(rm.free_regs) == 1
        assert len(rm.reg_bindings) == 3
        rm._check_invariants()
        rm.next_instruction()
        rm.possibly_free_vars([b0, b1, b2])
        rm._check_invariants()
        assert len(rm.free_regs) == 2
        assert len(rm.reg_bindings) == 2
        rm._check_invariants()
        rm.next_instruction()
        rm.possibly_free_vars([b0, b1, b2])
        rm._check_invariants()
        assert len(rm.free_regs) == 4
        assert len(rm.reg_bindings) == 0
        
        
