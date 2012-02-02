
from pypy.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic, LLtypeMixin

class TestVectorize(BaseTestBasic, LLtypeMixin):
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll:vectorize"

    def test_basic(self):
        ops = """
        [p0, p1, p2, i0, i1, i2]
        assert_aligned(p0, i0)
        assert_aligned(p1, i1)
        assert_aligned(p1, i2)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_1, descr=arraydescr)
        f2_1 = float_add(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)
        """
        expected = """
        [p0, p1, p2, i0, i1, i2]
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        vec0 = getarrayitem_vector_raw(p0, i0, descr=arraydescr)
        vec1 = getarrayitem_vector_raw(p1, i1, descr=arraydescr)
        vec2 = float_vector_add(vec0, vec1)
        setarrayitem_vector_raw(p2, i2, vec2, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)        
        """
        self.optimize_loop(ops, expected)

    def test_basic_sub(self):
        ops = """
        [p0, p1, p2, i0, i1, i2]
        assert_aligned(p0, i0)
        assert_aligned(p1, i1)
        assert_aligned(p1, i2)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_sub(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i3 = int_sub(i1_1, 2)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_1, descr=arraydescr)
        f2_1 = float_sub(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1, i3)
        """
        expected = """
        [p0, p1, p2, i0, i1, i2]
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i3 = int_sub(i1_1, 2)
        i2_1 = int_add(i2, 1)
        vec0 = getarrayitem_vector_raw(p0, i0, descr=arraydescr)
        vec1 = getarrayitem_vector_raw(p1, i1, descr=arraydescr)
        vec2 = float_vector_sub(vec0, vec1)
        setarrayitem_vector_raw(p2, i2, vec2, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1, i3)
        """
        self.optimize_loop(ops, expected)

    def test_unfit_trees(self):
        ops = """
        [p0, p1, p2, i0, i1, i2]
        assert_aligned(p0, i0)
        assert_aligned(p1, i1)
        assert_aligned(p1, i2)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i1_2 = int_add(1, i1_1)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_2, descr=arraydescr)
        f2_1 = float_add(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)
        """
        expected = """
        [p0, p1, p2, i0, i1, i2]
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i1_2 = int_add(1, i1_1)
        i2_1 = int_add(i2, 1)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_2, descr=arraydescr)
        f2_1 = float_add(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)
        """
        self.optimize_loop(ops, expected)

    def test_unfit_trees_2(self):
        ops = """
        [p0, p1, p2, i0, i1, i2]
        assert_aligned(p0, i0)
        assert_aligned(p1, i1)
        assert_aligned(p1, i2)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        setarrayitem_raw(p2, i2_1, f0_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)
        """
        expected = """
        [p0, p1, p2, i0, i1, i2]
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        setarrayitem_raw(p2, i2_1, f0_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)
        """
        self.optimize_loop(ops, expected)

    def test_unfit_trees_3(self):
        ops = """
        [p0, p1, p2, i0, i1, i2]
        assert_aligned(p0, i0)
        assert_aligned(p1, i1)
        assert_aligned(p1, i2)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_1, descr=arraydescr)
        f2_1 = float_sub(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)
        """
        expected = """
        [p0, p1, p2, i0, i1, i2]
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_1, descr=arraydescr)
        f2_1 = float_sub(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i1_1, i2_1)
        """
        self.optimize_loop(ops, expected)
        
    def test_guard_forces(self):
        ops = """
        [p0, p1, p2, i0, i1, i2]
        assert_aligned(p0, i0)
        assert_aligned(p1, i1)
        assert_aligned(p1, i2)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_1, descr=arraydescr)
        f2_1 = float_add(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        guard_true(i2_1) [p0, p1, p2, i0_1, i1_1, i2_1]
        finish(p0, p1, p2, i0_1, i1_1)
        """
        expected = """
        [p0, p1, p2, i0, i1, i2]
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        vec0 = getarrayitem_vector_raw(p0, i0, descr=arraydescr)
        vec1 = getarrayitem_vector_raw(p1, i1, descr=arraydescr)
        vec2 = float_vector_add(vec0, vec1)
        setarrayitem_vector_raw(p2, i2, vec2, descr=arraydescr)
        guard_true(i2_1) [p0, p1, p2, i0_1, i1_1, i2_1]
        finish(p0, p1, p2, i0_1, i1_1)
        """
        self.optimize_loop(ops, expected)

    def test_guard_prevents(self):
        ops = """
        [p0, p1, p2, i0, i1, i2]
        assert_aligned(p0, i0)
        assert_aligned(p1, i1)
        assert_aligned(p1, i2)
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        guard_true(i1) [p0, p1, p2, i1, i0, i2, f1, f2]
        i0_1 = int_add(i0, 1)
        i1_1 = int_add(1, i1)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, i1_1, descr=arraydescr)
        f2_1 = float_add(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i2_1)
        """
        expected = """
        [p0, p1, p2, i0, i1, i2]
        f0 = getarrayitem_raw(p0, i0, descr=arraydescr)
        f1 = getarrayitem_raw(p1, i1, descr=arraydescr)
        f2 = float_add(f0, f1)
        setarrayitem_raw(p2, i2, f2, descr=arraydescr)
        guard_true(i1) [p0, p1, p2, i1, i0, i2, f1, f2]
        i0_1 = int_add(i0, 1)
        i2_1 = int_add(i2, 1)
        f0_1 = getarrayitem_raw(p0, i0_1, descr=arraydescr)
        f1_1 = getarrayitem_raw(p1, 2, descr=arraydescr)
        f2_1 = float_add(f0_1, f1_1)
        setarrayitem_raw(p2, i2_1, f2_1, descr=arraydescr)
        finish(p0, p1, p2, i0_1, i2_1)
        """
        self.optimize_loop(ops, expected)
