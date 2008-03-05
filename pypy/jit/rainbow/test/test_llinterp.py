import py
from pypy.jit.conftest import option
from pypy.jit.rainbow.test import test_portal

if option.quicktest:
    py.test.skip("slow")



class TestLLInterpreted(test_portal.TestPortal):
    translate_support_code = True

    # for the individual tests see
    # ====> test_portal.py


    def test_vdict_and_vlist(self):
        py.test.skip("XXX")
        def ll_function():
            dic = {}
            lst = [12] * 3
            lst += []
            lst.append(13)
            lst.reverse()
            dic[12] = 34
            dic[lst[0]] = 35
            return dic[lst.pop()]
        res = self.timeshift_from_portal(ll_function, ll_function, [])
        assert res == ll_function()
        self.check_insns({})
