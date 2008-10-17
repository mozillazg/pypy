import py
from pypy.jit.rainbow.test.test_vdict import TestOOType as VDictTest
from pypy.jit.codegen.cli.test.test_gencli_interpreter import CompiledCliMixin

class TestVDictCli(CompiledCliMixin, VDictTest):

    # for the individual tests see
    # ====> ../../../rainbow/test/test_vdict.py

    pass
