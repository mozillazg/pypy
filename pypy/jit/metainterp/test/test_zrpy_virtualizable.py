import py
from test import test_virtualizable
from test.test_zrpy_basic import LLInterpJitMixin


class TestLLImplicitVirtualizable(LLInterpJitMixin,
                       test_virtualizable.ImplicitVirtualizableTests):
    pass
