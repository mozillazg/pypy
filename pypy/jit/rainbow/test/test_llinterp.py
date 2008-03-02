import py
from pypy.jit.conftest import option
from pypy.jit.rainbow.test import test_portal

if option.quicktest:
    py.test.skip("slow")



class TestLLInterpreted(test_portal.TestPortal):
    translate_support_code = True

    # for the individual tests see
    # ====> test_portal.py
