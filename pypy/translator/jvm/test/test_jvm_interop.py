from pypy.rlib.test.test_rjvm import BaseTestRJVM
from pypy.translator.jvm.test.runtest import JvmTest

import py

class TestRJVMCompilation(BaseTestRJVM, JvmTest):
    def test_static_method_no_overload(self):
        py.test.skip("Not supported yet.")

