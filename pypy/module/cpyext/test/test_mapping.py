from pypy.module.cpyext.test.test_api import BaseApiTest


class TestMapping(BaseApiTest):
    def test_keys(self, space, api):
        w_d = space.newdict()
        space.setitem(w_d, space.wrap("a"), space.wrap("a"))
        assert space.eq_w(api.PyMapping_Keys(w_d), space.wrap(["a"]))
