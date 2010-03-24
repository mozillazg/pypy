import py.test

from pypy.module.cpyext.test.test_cpyext import BaseApiTest

class TestTupleObject(BaseApiTest):
    def test_tupleobject(self, space, api):
        assert not api.PyTuple_Check(space.w_None)
        py.test.raises(TypeError, api.PyTuple_SetItem, space.w_None,
                0, space.w_None)
        api.PyTuple_SetItem(space.w_None, 0, space.w_None)
        #api.PyErr_Clear()
