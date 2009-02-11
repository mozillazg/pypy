from test.test_virtual import VirtualTests
from codegen386.test.test_basic import Jit386Mixin

class MyClass:
    pass

class TestsVirtual(Jit386Mixin, VirtualTests):
    # for the individual tests see
    # ====> ../../test/test_virtual.py
    _new_op = 'new_with_vtable'
    
    @staticmethod
    def _new():
        return MyClass()
