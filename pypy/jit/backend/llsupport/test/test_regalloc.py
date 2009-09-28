
from pypy.jit.metainterp.history import BoxInt, ConstInt
from pypy.jit.backend.llsupport.regalloc import RegisterManager, StackManager

def newboxes(*values):
    return [BoxInt(v) for v in values]

def boxes_and_longevity(num):
    res = []
    longevity = {}
    for i in range(num):
        box = BoxInt(0)
        res.append(box)
        longevity[box] = (0, 1)
    return res, longevity

class FakeReg(object):
    pass

r0, r1, r2, r3 = [FakeReg() for _ in range(4)]
regs = [r0, r1, r2, r3]

class TStackManager(StackManager):
    def stack_pos(self, i):
        return i

class MockAsm(object):
    def regalloc_store(self, from_loc, to_loc):
        pass

class TestRegalloc(object):
    def test_freeing_vars(self):
        b0, b1, b2 = newboxes(0, 0, 0)
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
        
    def test_register_exhaustion(self):
        boxes, longevity = boxes_and_longevity(5)
        rm = RegisterManager(regs, longevity)
        for b in boxes[:len(regs)]:
            assert rm.try_allocate_reg(b)
        assert rm.try_allocate_reg(boxes[-1]) is None
        rm._check_invariants()

    def test_need_lower_byte(self):
        boxes, longevity = boxes_and_longevity(5)
        b0, b1, b2, b3, b4 = boxes
        no_lower_byte_regs = [r2, r3]
        rm = RegisterManager(regs, longevity, no_lower_byte_regs)
        loc0 = rm.try_allocate_reg(b0, need_lower_byte=True)
        assert loc0 not in no_lower_byte_regs
        loc = rm.try_allocate_reg(b1, need_lower_byte=True)
        assert loc not in no_lower_byte_regs
        loc = rm.try_allocate_reg(b2, need_lower_byte=True)
        assert loc is None
        loc = rm.try_allocate_reg(b0, need_lower_byte=True)
        assert loc is loc0
        rm._check_invariants()

    def test_specific_register(self):
        boxes, longevity = boxes_and_longevity(5)
        rm = RegisterManager(regs, longevity)
        loc = rm.try_allocate_reg(boxes[0], selected_reg=r1)
        assert loc is r1
        loc = rm.try_allocate_reg(boxes[1], selected_reg=r1)
        assert loc is None
        rm._check_invariants()
        loc = rm.try_allocate_reg(boxes[0], selected_reg=r1)
        assert loc is r1
        loc = rm.try_allocate_reg(boxes[0], selected_reg=r2)
        assert loc is r2
        rm._check_invariants()

    def test_force_allocate_reg(self):
        boxes, longevity = boxes_and_longevity(5)
        b0, b1, b2, b3, b4 = boxes
        sm = TStackManager()
        rm = RegisterManager(regs, longevity,
                             no_lower_byte_regs = [r2, r3],
                             stack_manager=sm,
                             assembler=MockAsm())
        loc = rm.force_allocate_reg(b0, [])
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b1, [])
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b2, [])
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b3, [])
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b4, [])
        assert isinstance(loc, FakeReg)
        # one of those should be now somewhere else
        locs = [rm.loc(b) for b in boxes]
        used_regs = [loc for loc in locs if isinstance(loc, FakeReg)]
        assert len(used_regs) == len(regs)
        loc = rm.force_allocate_reg(b0, [], need_lower_byte=True)
        assert isinstance(loc, FakeReg)
        assert loc not in [r2, r3]
        rm._check_invariants()
        
