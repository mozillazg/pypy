import py
from pypy.jit.codewriter import support
from pypy.jit.codewriter.flatten import flatten_graph
from pypy.jit.codewriter.format import format_assembler


class FakeRegAlloc:
    # a RegAllocator that answers "0, 1, 2, 3, 4..." for the colors
    def __init__(self):
        self.seen = {}
        self.num_colors = 0
    def getcolor(self, v):
        if v not in self.seen:
            self.seen[v] = self.num_colors
            self.num_colors += 1
        return self.seen[v]


class TestFlatten:

    def make_graphs(self, func, values, type_system='lltype'):
        self.rtyper = support.annotate(func, values, type_system=type_system)
        return self.rtyper.annotator.translator.graphs

    def encoding_test(self, func, args, expected, optimize=True):
        graphs = self.make_graphs(func, args)
        ssarepr = flatten_graph(graphs[0], FakeRegAlloc())
        asm = format_assembler(ssarepr)
        expected = str(py.code.Source(expected)).strip() + '\n'
        assert asm == expected

    def test_simple(self):
        def f(n):
            return n + 10
        self.encoding_test(f, [5], """
            int_add %i0, $10, %i1
            int_return %i1
        """)

    def test_loop(self):
        def f(a, b):
            while a > 0:
                b += a
                a -= 1
            return b
        self.encoding_test(f, [5, 6], """
            int_rename [%i0, %i1], [%i2, %i3]
            L1:
            int_gt %i2, $0, %i4
            goto_if_not L2, %i4
            int_rename [%i2, %i3], [%i5, %i6]
            int_add %i6, %i5, %i7
            int_sub %i5, $1, %i8
            int_rename [%i8, %i7], [%i2, %i3]
            goto L1
            L2:
            int_return %i3
        """)
