
from test.test_vbool import BoolTests
from codegen386.test.test_basic import Jit386Mixin

class TestVBool(Jit386Mixin, BoolTests):
    pass
