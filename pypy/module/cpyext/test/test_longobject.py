
import sys

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.module.cpyext.test.test_api import BaseApiTest


class TestLongObject(BaseApiTest):
    def test_FromLong(self, space, api):
        value = api.PyLong_FromLong(3)
        assert isinstance(value, W_IntObject)
        assert space.unwrap(value) == 3

        value = api.PyLong_FromLong(sys.maxint + 1)
        assert isinstance(value, W_LongObject)
        assert space.unwrap(value) == sys.maxint + 1 # should obviously fail but doesnt
    def test_asulong(self, space, api):
        w_value = api.PyLong_FromLong((sys.maxint - 1) / 2)
        w_value = space.mul(w_value, space.wrap(4))
        value = api.PyLong_AsUnsignedLong(w_value)
        assert value == (sys.maxint - 1) * 2
