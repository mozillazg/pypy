

from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestIterator(AppTestCpythonExtensionBase):
    def test_iterator(self):
        import sys
        module = self.import_extension('foo', [
            ("newiter", "METH_VARARGS",
             '''
             return PySequence_Fast(PyTuple_GetItem(args, 0), "message");
             '''
             ),
            ("fast_getitem", "METH_VARARGS",
             '''
             PyObject *lst = PyTuple_GetItem(args, 0);
             long index = PyInt_AsLong(PyTuple_GetItem(args, 1));
             return PySequence_Fast_GET_ITEM(lst, index);
             '''
             ),
            ("fast_getsize", "METH_VARARGS",
             '''
             PyObject *lst = PyTuple_GetItem(args, 0);
             return PyInt_FromLong(PySequence_Fast_GET_SIZE(lst));
             '''
             ),
            ])
        t = (1, 2, 3, 4)
        assert module.newiter(t) is t
        l = [1, 2, 3, 4]
        assert module.newiter(l) is l
        assert isinstance(module.newiter(set([1, 2, 3])), tuple)
        assert sorted(module.newiter(set([1, 2, 3]))) == [1, 2, 3]
        try:
            module.newiter(3)
        except TypeError, te:
            assert te.args == ("message",)
        else:
            raise Exception("DID NOT RAISE")
        assert module.fast_getitem((1, 2, 3), 1) == 2
        assert module.fast_getsize([1, 2, 3]) == 3
