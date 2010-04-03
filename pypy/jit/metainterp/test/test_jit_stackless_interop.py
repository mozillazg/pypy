import py
import os
import sys
from pypy.rlib.jit import JitDriver, OPTIMIZER_SIMPLE, OPTIMIZER_FULL
from pypy.rlib.objectmodel import compute_hash
from pypy.jit.metainterp.warmspot import ll_meta_interp, get_stats, jittify_and_run, WarmRunnerDesc
from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import history
from pypy.translator.stackless.code import yield_current_frame_to_caller
from pypy.translator.translator import TranslationContext, graphof
from pypy.annotation.listdef import s_list_of_strings
from pypy.translator.stackless.transform import StacklessTransformer, FrameTyper
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.translator.c import gc
from pypy.rpython.test.test_llinterp import get_interpreter, clear_tcache
from pypy import conftest
from pypy.rlib.jit import DEBUG_STEPS, DEBUG_DETAILED, DEBUG_OFF, DEBUG_PROFILE
from pypy.translator.stackless.code import UnwindException

optimizer = OPTIMIZER_SIMPLE

def meta_interp(f, args=(), policy=None):
    return ll_meta_interp(f, args, optimizer=optimizer,
                          policy=policy,
                          CPUClass=runner.LLtypeCPU,
                          type_system='lltype')

def test_simple_unwind():
    myjitdriver = JitDriver(greens = [], reds = ['y', 'x'])

    def g(z):
        if z % 2:
            parent = yield_current_frame_to_caller()
            return parent
        else:
            return None

    def f(y):
        x = 0
        while y > 0:
            myjitdriver.can_enter_jit(x=x, y=y)
            myjitdriver.jit_merge_point(x=x, y=y)

            try:
                res = g(y)
                if res is not None:
                    res = res.switch()
                if res is None:
                    x += 1
            except UnwindException:
                pass
            y -= 1
        return x
    res = meta_interp(f, [100])
    assert res == 100
