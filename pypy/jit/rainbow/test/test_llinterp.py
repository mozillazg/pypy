import py
from pypy.jit.conftest import option
from pypy.jit.rainbow.test import test_portal, test_virtualizable

if option.quicktest:
    py.test.skip("slow")


class TestLLInterpretedOOType(test_portal.TestPortalOOType):
    translate_support_code = True

    # for the individual tests see
    # ====> test_portal.py

    def skip(self):
        py.test.skip('in progress')
        
    test_dfa_compile = skip
    test_dfa_compile2 = skip
    test_dfa_compile3 = skip
    test_multiple_portal_calls = skip
    test_cast_ptr_to_int = skip
    test_residual_red_call_with_promoted_exc = skip
    test_residual_oop_raising = skip
    test_simple_recursive_portal_call = skip
    test_simple_recursive_portal_call2 = skip
    test_recursive_portal_call = skip
    test_indirect_call_voidargs = skip
    test_vdict_and_vlist = skip



class TestLLInterpretedLLType(test_portal.TestPortalLLType):
    translate_support_code = True

    # for the individual tests see
    # ====> test_portal.py


class TestLLVirtualizable(test_virtualizable.TestVirtualizableImplicit):
    translate_support_code = True

    # for the individual tests see
    # ====> test_virtualizable.py
