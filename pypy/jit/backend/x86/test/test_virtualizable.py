
import py
from test.test_virtualizable import TestLLtype as BaseTest
from codegen386.test.test_basic import Jit386Mixin

py.test.skip("xxx")

class TestVirtualizable(Jit386Mixin, BaseTest):
    pass
