
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.optimizeopt import optimize_trace
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer,\
     PtrOptValue, LEVEL_KNOWNCLASS
from rpython.jit.metainterp.optimizeopt.unroll import Unroller
from rpython.jit.metainterp.optimizeopt.test.test_util import BaseTest,\
     FakeMetaInterpStaticData, LLtypeMixin
from rpython.jit.metainterp.optimizeopt.pure import OptPure
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.history import ConstInt, BoxInt
from rpython.jit.backend.llgraph import runner
from rpython.jit.codewriter.heaptracker import adr2int

class TestUnrollDirect(BaseTest, LLtypeMixin):
    cpu = runner.LLGraphCPU(None)
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"
    metainterp_sd = FakeMetaInterpStaticData(cpu)

    def parse(self, loop):
        return BaseTest.parse(self, loop, postprocess=self.postprocess)

    def optimize(self, loop, expected=None, unroller=None):
        if isinstance(loop, str):
            loop = self.parse(loop)
        state = optimize_trace(self.metainterp_sd, None, loop, self.enable_opts,
                               unroller=unroller)
        if expected is not None:
            expected = self.parse(expected)
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
        unroller.optimizer._newoperations = [
            ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1)
        ]
        pure.optimizer = unroller.optimizer
        expected = """
        [i0, i1]
        label(i0, i1)
        escape(i1)
        jump(i0, i1)
        """
        self.optimize(loop, expected, unroller=unroller)

    def test_inherit_known_class(self):
        loop = self.parse("""
        [p0]
        label(p0)
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """)
        expected = """
        [p0]
        label(p0)
        jump(p0)
        """
        p0 = loop.inputargs[0]
        unroller = Unroller()
        unroller.optimizer = Optimizer(self.metainterp_sd, None, None, [])
        cls = adr2int(self.node_vtable_adr)
        unroller.optimizer.values = {
            p0: PtrOptValue(p0, known_class=ConstInt(cls),
                            level=LEVEL_KNOWNCLASS),
        }
        self.optimize(loop, expected, unroller=unroller)
