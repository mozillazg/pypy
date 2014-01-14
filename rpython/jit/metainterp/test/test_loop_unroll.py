import py
from rpython.rlib.jit import JitDriver
from rpython.jit.metainterp.test import test_loop
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.metainterp.optimizeopt import ALL_OPTS_NAMES

class LoopUnrollTest(test_loop.LoopTest):
    enable_opts = ALL_OPTS_NAMES

    automatic_promotion_result = {
        'int_gt': 1, 'guard_false': 1, 'jump': 1, 'int_add': 3,
        'guard_value': 1
    }

    # ====> test_loop.py

class TestLLtype(LoopUnrollTest, LLJitMixin):
    pass
