from pypy.rlib.jit import JitDriver, hint
from pypy.jit.hintannotator.policy import StopAtXPolicy
from pypy.jit.rainbow.test.test_hotpath import HotPathTest
from pypy.jit.rainbow.graphopt import simplify_virtualizable_accesses
from pypy.jit.rainbow.graphopt import is_vable_setter, is_vable_getter


class XY(object):
    _virtualizable_ = True

    def __init__(self, x, y):
        self.x = x
        self.y = y


class TestGraphOpt(HotPathTest):

    def _run(self, main, main_args):
        # don't execute the tests.  Instead we apply graphopt and count the
        # remaining non-optimized accesses.
        simplify_virtualizable_accesses(self.writer)
        self.setters = {}
        self.getters = {}
        for graph in self.rtyper.annotator.translator.graphs:
            settercount = 0
            gettercount = 0
            for block in graph.iterblocks():
                for op in block.operations:
                    if is_vable_setter(op):
                        settercount += 1
                    elif is_vable_getter(op):
                        gettercount += 1
            func = graph.func
            self.setters[func] = self.setters.get(func, 0) + settercount
            self.getters[func] = self.getters.get(func, 0) + gettercount

    def test_simple_case(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['xy', 'i', 'res']

        def f(xy):
            i = 1024
            while i > 0:
                i >>= 1
                res = xy.x+xy.y
                MyJitDriver.jit_merge_point(xy=xy, res=res, i=i)
                MyJitDriver.can_enter_jit(xy=xy, res=res, i=i)
            return res

        def main(x, y):
            xy = XY(x, y)
            return f(xy)

        self.run(main, [20, 30], 2)
        assert self.setters[XY.__init__.im_func] == 0
        assert self.getters[f] == 0

    def test_through_residual(self):
        class MyJitDriver(JitDriver):
            greens = []
            reds = ['xy', 'i', 'res']

        def debug(xy):
            xy.x = 5
            return xy.y

        def f(xy):
            i = 1024
            while i > 0:
                i >>= 1
                res = xy.x+xy.y
                debug(xy)
                MyJitDriver.jit_merge_point(xy=xy, res=res, i=i)
                MyJitDriver.can_enter_jit(xy=xy, res=res, i=i)
            return res

        def main(x, y):
            xy = XY(x, y)
            return f(xy)

        self.run(main, [20, 30], 2, policy=StopAtXPolicy(debug))
        assert self.setters[XY.__init__.im_func] == 0
        assert self.getters[f] == 0
        assert self.setters[debug] == 1
        assert self.getters[debug] == 1
