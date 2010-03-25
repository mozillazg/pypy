from pypy.module.cpyext.test.test_api import BaseApiTest

class TestTupleObject(BaseApiTest):
    def test_tupleobject(self, space, api):
        assert not api.PyTuple_Check(space.w_None)
        assert api.PyTuple_SetItem(space.w_None, 0, space.w_None) == -1
        api.PyErr_Clear()
