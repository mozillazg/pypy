
from test.test_slist import ListTests
from codegen386.test.test_basic import Jit386Mixin

class TestSList(Jit386Mixin, ListTests):
    pass
