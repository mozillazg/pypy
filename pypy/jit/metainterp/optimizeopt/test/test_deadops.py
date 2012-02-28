
from pypy.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from pypy.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic

class TestRemoveDeadOps(BaseTestBasic, LLtypeMixin):
    def test_deadops(self):
        ops = """
        [i0]
        i1 = int_add(i0, 1)
        jump()
        """
        expected = """
        [i0]
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_not_deadops(self):
        ops = """
        [i0]
        i1 = int_add(i0, 1)
        jump(i1)
        """
        expected = """
        [i0]
        i1 = int_add(i0, 1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_not_deadops_1(self):
        ops = """
        [i0]
        i1 = int_add(i0, 1)
        guard_true(i0) [i1]
        jump()
        """
        expected = """
        [i0] 
        i1 = int_add(i0, 1)
        guard_true(i0) [i1]
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_not_deadops_2(self):
        ops = """
        [p0, i0]
        setfield_gc(p0, i0)
        jump()
        """
        expected = """
        [p0, i0]
        setfield_gc(p0, i0)
        jump()
        """
        self.optimize_loop(ops, expected)
