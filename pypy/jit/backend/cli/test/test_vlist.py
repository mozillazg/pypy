import py
from pypy.jit.metainterp.test import test_vlist
from pypy.jit.backend.cli.test.test_basic import CliJitMixin


class TestVlist(CliJitMixin, test_vlist.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_vlist.py

    def skip(self):
        py.test.skip("works only after translation")

    def _skip(self):
        py.test.skip("in-progress")

    test_list_pass_around = _skip
    test_cannot_be_virtual = _skip
    test_ll_fixed_setitem_fast = _skip
