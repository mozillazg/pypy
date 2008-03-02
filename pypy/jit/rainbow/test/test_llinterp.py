import py; py.test.skip("in-progress")
from pypy.jit.rainbow.test import test_portal


class TestLLInterpreted(test_portal.TestPortal):
    translate_support_code = True

    # for the individual tests see
    # ====> test_portal.py
