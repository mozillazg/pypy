
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.optimizeopt import optimize_trace
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer
from rpython.jit.metainterp.optimizeopt.unroll import Unroller
from rpython.jit.metainterp.optimizeopt.test.test_util import BaseTest,\
     FakeMetaInterpStaticData
from rpython.jit.metainterp.optimizeopt.pure import OptPure
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import ConstInt, BoxInt
from rpython.jit.backend.llgraph import runner

class TestUnrollDirect(BaseTest):
    cpu = runner.LLGraphCPU(None)
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"
    metainterp_sd = FakeMetaInterpStaticData(cpu)

    def optimize(self, loop, expected=None, unroller=None):
        if isinstance(loop, str):
            loop = parse(loop)
        state = optimize_trace(self.metainterp_sd, None, loop, self.enable_opts,
                               unroller=unroller)
        if expected is not None:
            expected = parse(expected)
            self.assert_equal(loop, expected)
        return state
    
    def test_basic_unroll(self):
        preamble = """
        [i0]
        label(i0)
        i1 = int_add(i0, 1)
        label(i1)
        """
        unroller = self.optimize(preamble)
        loop = """
        [i0]
        label(i0)
        i1 = int_add(i0, 1)
        jump(i1)
        """
        self.optimize(loop, loop, unroller=unroller)
        
    def test_pure_opts(self):
        loop = parse("""
        [i0]
        label(i0)
        i1 = int_add(i0, 1)
        escape(i1)
        jump(i0)
        """)
        pure = OptPure()
        i0 = loop.operations[1].getarg(0)
        i1 = BoxInt()
        unroller = Unroller()
        unroller.optimizer = Optimizer(self.metainterp_sd, None, None, [pure])
        pure.optimizer = unroller.optimizer
        pure.pure(rop.INT_ADD, [i0, ConstInt(1)], i1)
        expected = """
        [i0, i1]
        label(i0, i1)
        escape(i1)
        jump(i0, i1)
        """
        self.optimize(loop, expected, unroller=unroller)
