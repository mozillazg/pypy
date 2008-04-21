import py
from pypy.jit.conftest import option
from pypy.jit.rainbow.test import test_portal, test_virtualizable

if option.quicktest:
    py.test.skip("slow")



class TestLLInterpreted(test_portal.TestPortalLLType):
    translate_support_code = True

    # for the individual tests see
    # ====> test_portal.py


class TestLLVirtualizable(test_virtualizable.TestVirtualizableImplicit):
    translate_support_code = True

    # for the individual tests see
    # ====> test_virtualizable.py
