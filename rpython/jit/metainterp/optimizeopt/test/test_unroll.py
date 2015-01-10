
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.optimizeopt import optimize_trace
from rpython.jit.metainterp.optimizeopt.test.test_util import BaseTest,\
     FakeMetaInterpStaticData
from rpython.jit.backend.llgraph import runner

class TestUnrollDirect(BaseTest):
    cpu = runner.LLGraphCPU(None)
    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll"

    def optimize(self, loop, expected=None, export_state=False, start_state=None):
        metainterp_sd = FakeMetaInterpStaticData(self.cpu)
        loop = parse(loop)
        state = optimize_trace(metainterp_sd, None, loop, self.enable_opts,
                               export_state=export_state, start_state=start_state)
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
        exported_state = self.optimize(preamble, export_state=True)
        loop = """
        [i0]
        label(i0)
        i1 = int_add(i0, 1)
        jump(i1)
        """
        self.optimize(loop, loop, start_state=exported_state)
        
