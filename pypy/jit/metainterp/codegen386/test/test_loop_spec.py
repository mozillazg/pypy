import py
from codegen386.runner import CPU386
from pyjitpl import ll_meta_interp
from test import test_loop_spec

class TestLoopSpec(test_loop_spec.TestLoopSpec):
    # for the individual tests see
    # ====> ../../test/test_loop.py

    def meta_interp(self, f, args, requires_oo=False):
        ###py.test.skip("in-progress")
        if requires_oo:
            py.test.skip("oo only")
        return ll_meta_interp(f, args, CPUClass=CPU386)
