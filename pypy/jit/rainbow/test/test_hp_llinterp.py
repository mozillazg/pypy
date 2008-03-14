

import py
from pypy.jit.conftest import option
from pypy.jit.rainbow.test import test_hotpath, test_hp_promotion

if option.quicktest:
    py.test.skip("slow")


py.test.skip("in-progress")

class TestLLInterpreted(test_hotpath.TestHotPath):
    translate_support_code = True

    # for the individual tests see
    # ====> test_hotpath.py


class TestLLInterpreted(test_hp_promotion.TestHotPromotion):
    translate_support_code = True

    # for the individual tests see
    # ====> test_hp_promotion.py
