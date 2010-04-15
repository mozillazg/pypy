from pypy.jit.metainterp import support
from pypy.jit.metainterp.codewriter2 import BytecodeMaker


class TestBytecodeMaker:

    def make_graphs(self, func, values, type_system='lltype'):
        self.rtyper = support.annotate(func, values, type_system=type_system)
        return self.rtyper.annotator.translator.graphs

    def coloring_test(self, func, args, expected_lambda):
        graphs = self.make_graphs(func, args)
        maker = BytecodeMaker(graphs[0])
        maker.register_allocation()
        expected = expected_lambda(graphs[0].startblock)
        for v, num in expected.items():
            print '\t%s\tcolor %d\texpected %d' % (v, maker.getcolor(v), num)
        for v, num in expected.items():
            assert maker.getcolor(v) == num

    def encoding_test(self, func, args, expected):
        graphs = self.make_graphs(func, args)
        maker = BytecodeMaker(graphs[0])
        maker.generate()
        asm = maker.format_assembler()
        expected = str(py.code.Source(expected)).strip()
        assert asm == expected + '\n'

    def test_coloring_simple(self):
        def f(n):
            return n + 10
        self.coloring_test(f, [5],
            lambda startblock:
                {startblock.inputargs[0]: 0,
                 startblock.operations[0].result: 0,
                 startblock.exits[0].target.inputargs[0]: 0})

    def test_coloring_bigblock(self):
        def f(a, b, c):
            return (((a + 10) * 2) + (b - c)) * a
        self.coloring_test(f, [5, 6, 7],
            lambda startblock:
                {startblock.inputargs[0]: 0,
                 startblock.inputargs[1]: 1,
                 startblock.inputargs[2]: 2,
                 startblock.operations[0].result: 3,
                 startblock.operations[1].result: 3,
                 startblock.operations[2].result: 1,
                 startblock.operations[3].result: 1,
                 startblock.operations[4].result: 0,
                 startblock.exits[0].target.inputargs[0]: 0})

    def test_bytecodemaker_generate_simple(self):
        def f(n):
            return n + 10
        self.encoding_test(f, [5], """
            [%i0]
            int_add %i0, $10, %i0
            int_return %i0
        """)

    def test_bytecodemaker_generate_bigblock(self):
        def f(a, b, c):
            return (((a + 10) * 2) + (b - c)) * a
        self.encoding_test(f, [5, 6, 7], """
            [%i0, %i1, %i2]
            int_add %i0, $10, %i3
            int_mul %i3, $2, %i3
            int_sub %i1, %i2, %i1
            int_add %i3, %i1, %i1
            int_mul %i1, %i0, %i0
            int_return %i0
        """)

    def test_bytecodemaker_generate_loop(self):
        def f(a, b):
            while a > 0:
                b += a
                a -= 1
            return b
        self.encoding_test(f, [5, 6], """
            [%i0, %i1]
            L0:
            goto_if_not_int_gt %i0, $0, L1
            int_add %i1, %i0, %i1
            int_sub %i0, $1, %i0
            goto L0
            L1:
            int_return %i1
        """)

    def test_bytecodemaker_generate_swap(self):
        def f(a, b):
            while a > 0:
                a, b = b, b+a
            return b
        self.encoding_test(f, [5, 6], """
            [%i0, %i1]
            L0:
            goto_if_not_int_gt %i0, $0, L1
            int_add %i1, %i0, %i0
            int_swap %i0, %i1
            goto L0
            L1:
            int_return %i1
        """)

    def test_bytecodemaker_generate_cycle(self):
        def f(a, b, c):
            while a > 0:
                a, b, c = b, c, a
            return b
        self.encoding_test(f, [5, 6, 7], """
            [%i0, %i1, %i2]
            L0:
            goto_if_not_int_gt %i0, $0, L1
            int_swap_cycle [%i0, %i2, %i1]
            goto L0
            L1:
            int_return %i1
        """)

    def test_bytecodemaker_generate_same_as_var(self):
        def f(a, b, c):
            while a > 0:
                b = c
            return b
        self.encoding_test(f, [5, 6, 7], """
            [%i0, %i1, %i2]
            L0:
            goto_if_not_int_gt %i0, $0, L1
            int_same_as %i2, %i1
            goto L0
            L1:
            int_return %i1
        """)

    def test_bytecodemaker_generate_same_as_const(self):
        def f(a, b):
            while a > 0:
                b = -17
            return b
        self.encoding_test(f, [5, 6], """
            [%i0, %i1]
            L0:
            goto_if_not_int_gt %i0, $0, L1
            int_same_as $-17, %i1
            goto L0
            L1:
            int_return %i1
        """)

    def test_bytecodemaker_generate_return_const(self):
        def f(a, b):
            if a > b:
                b = -17
            return 1 + b
        self.encoding_test(f, [5, 6], """
            [%i0, %i1]
            goto_if_not_int_gt %i0, %i1, L1
            int_return $-16
            L1:
            int_add $1, %i1, %i0
            int_return %i0
        """)
