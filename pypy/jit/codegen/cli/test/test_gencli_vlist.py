import py
from pypy.jit.rainbow.test.test_vlist import TestOOType as VListTest
from pypy.jit.codegen.cli.test.test_gencli_interpreter import CompiledCliMixin

class TestVListCli(CompiledCliMixin, VListTest):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_vlist.py

    def skip(self):
        py.test.skip('in progress')

    def test_force_fixed(self):
        py.test.skip("very strange bug, crashes both mono and .NET")
