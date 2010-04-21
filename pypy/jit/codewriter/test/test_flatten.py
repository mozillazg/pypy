import py
from pypy.jit.codewriter import support
from pypy.jit.codewriter.flatten import flatten_graph, reorder_renaming_list
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

def test_reorder_renaming_list():
    result = reorder_renaming_list([], [])
    assert result == []
    result = reorder_renaming_list([1, 2, 3], [4, 5, 6])
    assert result == [(1, 4), (2, 5), (3, 6)]
    result = reorder_renaming_list([4, 5, 1, 2], [1, 2, 3, 4])
    assert result == [(1, 3), (4, 1), (2, 4), (5, 2)]
    result = reorder_renaming_list([1, 2], [2, 1])
    assert result == None
    result = reorder_renaming_list([4, 3, 1, 2, 6], [1, 2, 3, 4, 5])
    assert result == None


class TestFlatten:

    def make_graphs(self, func, values, type_system='lltype'):
        self.rtyper = support.annotate(func, values, type_system=type_system)
        return self.rtyper.annotator.translator.graphs

    def encoding_test(self, func, args, expected, optimize=True):
        graphs = self.make_graphs(func, args)
        ssarepr = flatten_graph(graphs[0], {'int': FakeRegAlloc(),
                                            'ref': FakeRegAlloc(),
                                            'float': FakeRegAlloc()})
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
            int_copy %i0, %i2
            int_copy %i1, %i3
            L1:
            int_gt %i2, $0, %i4
            goto_if_not L2, %i4
            int_copy %i2, %i5
            int_copy %i3, %i6
            int_add %i6, %i5, %i7
            int_sub %i5, $1, %i8
            int_copy %i8, %i2
            int_copy %i7, %i3
            goto L1
            L2:
            int_return %i3
        """)

    def test_float(self):
        def f(i, f):
            return (i*5) + (f*0.25)
        self.encoding_test(f, [4, 7.5], """
            int_mul %i0, $5, %i1
            float_mul %f0, $0.25, %f1
            cast_int_to_float %i1, %f2
            float_add %f2, %f1, %f3
            float_return %f3
        """)
