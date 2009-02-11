import py
from test import test_slist
from test.test_zrpy_basic import LLInterpJitMixin


class TestLLList(test_slist.ListTests, LLInterpJitMixin):
    pass
