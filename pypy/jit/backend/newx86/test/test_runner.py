import py
from pypy.jit.backend.newx86.runner import CPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest

class FakeStats(object):
    pass

# ____________________________________________________________

class TestX86(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py
    
    def setup_method(self, meth):
        self.cpu = CPU(rtyper=None, stats=FakeStats())
