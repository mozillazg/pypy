from pypy.jit.codewriter import support
from pypy.jit.codewriter.liveness import compute_liveness
from pypy.jit.codewriter.test.test_flatten import fake_regallocs
from pypy.jit.codewriter.flatten import flatten_graph, ListOfKind
from pypy.jit.codewriter.format import assert_format
from pypy.objspace.flow.model import SpaceOperation


class TestFlatten:

    def make_graphs(self, func, values, type_system='lltype'):
        self.rtyper = support.annotate(func, values, type_system=type_system)
        return self.rtyper.annotator.translator.graphs

    def add_G_prefix(self, graph):
        """Add a 'G_' prefix to the opnames 'int_add' and 'int_mul'.
        Turn the arguments of float_add into a ListOfKind()."""
        def with_prefix(op):
            if op.opname in ('int_add', 'int_mul'):
                return SpaceOperation('G_' + op.opname, op.args, op.result)
            if op.opname == 'float_add':
                return SpaceOperation(op.opname,
                                      [ListOfKind('float', op.args)],
                                      op.result)
            return op
        #
        for block in graph.iterblocks():
            if block.operations:
                block.operations = map(with_prefix, block.operations)

    def encoding_test(self, func, args, expected,
                      switches_require_liveness=False):
        graphs = self.make_graphs(func, args)
        self.add_G_prefix(graphs[0])
        compute_liveness(graphs[0], switches_require_liveness)
        ssarepr = flatten_graph(graphs[0], fake_regallocs())
        assert_format(ssarepr, expected)

    def test_simple_no_live(self):
        def f(n):
            return n + 10
        self.encoding_test(f, [5], """
            -live-
            G_int_add %i0, $10, %i1
            int_return %i1
        """)

    def test_simple(self):
        def f(n):
            return (n + 10) * (n + 3) * (n + 6)
        self.encoding_test(f, [5], """
            -live- %i0
            G_int_add %i0, $10, %i1
            -live- %i0, %i1
            G_int_add %i0, $3, %i2
            -live- %i0
            G_int_mul %i1, %i2, %i3
            -live- %i3
            G_int_add %i0, $6, %i4
            -live-
            G_int_mul %i3, %i4, %i5
            int_return %i5
        """)

    def test_one_path(self):
        def f(x, y):
            if x+5:
                return x+1
            return y+2
        self.encoding_test(f, [5, 6], """
            -live- %i0, %i1
            G_int_add %i0, $5, %i2
            int_is_true %i2, %i3
            goto_if_not %i3, L1
            int_copy %i0, %i4
            -live-
            G_int_add %i4, $1, %i5
            int_return %i5
            L1:
            int_copy %i1, %i6
            -live-
            G_int_add %i6, $2, %i7
            int_return %i7
        """)

    def test_other_path(self):
        def f(x, y):
            if x+5:
                return x+y
            return x+2
        self.encoding_test(f, [5, 6], """
            -live- %i0, %i1
            G_int_add %i0, $5, %i2
            int_is_true %i2, %i3
            goto_if_not %i3, L1
            int_copy %i0, %i4
            int_copy %i1, %i5
            -live-
            G_int_add %i4, %i5, %i6
            int_return %i6
            L1:
            int_copy %i0, %i7
            -live-
            G_int_add %i7, $2, %i8
            int_return %i8
        """)

    def test_no_path(self):
        def f(x, y):
            if x+y:
                return x+5
            return x+2
        self.encoding_test(f, [5, 6], """
            -live- %i0
            G_int_add %i0, %i1, %i2
            int_is_true %i2, %i3
            goto_if_not %i3, L1
            int_copy %i0, %i4
            -live-
            G_int_add %i4, $5, %i5
            int_return %i5
            L1:
            int_copy %i0, %i6
            -live-
            G_int_add %i6, $2, %i7
            int_return %i7
        """)

    def test_switch_require_liveness(self):
        def f(x, y):
            if x:
                return x
            return y
        self.encoding_test(f, [5, 6], """
            int_is_true %i0, %i2
            -live- %i0, %i1
            goto_if_not %i2, L1
            int_return %i0
            L1:
            int_return %i1
        """, switches_require_liveness=True)

    def test_list_of_kind(self):
        def f(x, y, z, t):
            return (x + y) * (z + t)
        self.encoding_test(f, [5, 6, 3.2, 4.3], """
            -live- %f0, %f1
            G_int_add %i0, %i1, %i2
            float_add F[%f0, %f1], %f2
            cast_int_to_float %i2, %f3
            float_mul %f3, %f2, %f4
            float_return %f4
        """)
