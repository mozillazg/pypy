
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
        assert space.unwrap(value) == sys.maxint + 1
