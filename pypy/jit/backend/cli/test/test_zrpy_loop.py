import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_loop


class TestLoop(CliTranslatedJitMixin, test_loop.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py

    def skip(self):
        py.test.skip('in-progress')

    test_interp_many_paths = skip
    test_interp_many_paths_2 = skip
    test_loop_unicode = skip
