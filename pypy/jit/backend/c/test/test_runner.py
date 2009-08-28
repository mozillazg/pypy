from pypy.jit.backend.c.runner import CPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest

class FakeStats(object):
    pass


class TestC(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py

    def setup_class(cls):
        cls.cpu = CPU(rtyper=None, stats=FakeStats())
