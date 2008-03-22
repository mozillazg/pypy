

import py
from pypy.jit.conftest import option

if option.quicktest:
    py.test.skip("slow")


def llinterp(unbound_method):
    cls = unbound_method.im_class
    cls.setup_class.im_func(cls)
    try:
        self = cls()
        self.translate_support_code = True
        unbound_method(self)
    finally:
        cls.teardown_class.im_func(cls)

# ____________________________________________________________
# it takes ages to run all these tests, and a few of them are more or less
# enough to pinpoint all the translation issues

def test_simple_loop():
    from pypy.jit.rainbow.test.test_hotpath import TestHotPath
    llinterp(TestHotPath.test_simple_loop)

def test_hp_tlr():
    from pypy.jit.rainbow.test.test_hotpath import TestHotPath
    llinterp(TestHotPath.test_hp_tlr)

def test_green_across_global_mp():
    from pypy.jit.rainbow.test.test_hp_promotion import TestHotPromotion
    llinterp(TestHotPromotion.test_green_across_global_mp)

def test_simple_interpreter_with_frame_with_stack():
    from pypy.jit.rainbow.test.test_hp_virtualizable import TestVirtualizableImplicit
    llinterp(TestVirtualizableImplicit.test_simple_interpreter_with_frame_with_stack)
