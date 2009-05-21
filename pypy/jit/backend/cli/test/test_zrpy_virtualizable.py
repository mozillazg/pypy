import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_virtualizable


class TestVirtualizable(CliTranslatedJitMixin, test_virtualizable.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_virtualizable.py

    def skip(self):
        py.test.skip('in-progress')

    test_virtual_on_virtualizable = skip
    test_no_virtual_on_virtualizable = skip
    test_unequal_list_lengths_cannot_be_virtual = skip
    test_virtualizable_hierarchy = skip
    test_non_virtual_on_always_virtual = skip
    test_external_pass = skip
    test_always_virtual_with_origfields = skip
    test_pass_always_virtual_to_bridge = skip
