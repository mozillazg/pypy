from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext import sequence

class TestIterator(BaseApiTest):
    def test_index(self, space, api):
        assert api.PyIndex_Check(space.wrap(12))
        assert not api.PyIndex_Check(space.wrap('12'))
