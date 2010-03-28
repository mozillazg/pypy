from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestDictObject(AppTestCpythonExtensionBase):
    def test_dict(self):
        module = self.import_extension("foo", [
        ("test_dict_create", "METH_NOARGS",
        """
            PyObject *p = PyDict_New();
            return p;
        """),
        ("test_dict_getitem", "METH_VARARGS",
        """
            return PyDict_GetItem(PyTuple_GetItem(args, 0), PyTuple_GetItem(args, 1));
        """),
        ("test_dict_setitem", "METH_VARARGS",
        """
            PyDict_SetItem(
                PyTuple_GetItem(args, 0),
                PyTuple_GetItem(args, 1),
                PyTuple_GetItem(args, 2)
            );
            Py_RETURN_NONE;
        """),
        ("dict_getitem_str", "METH_VARARGS",
         """
         return PyDict_GetItemString(PyTuple_GetItem(args, 0), "name");
         """
         ),
        ])
        
        assert module.test_dict_create() == {}
        assert module.test_dict_getitem({"a": 72}, "a") == 72
        d = {}
        module.test_dict_setitem(d, "c", 72)
        assert d["c"] == 72
        d["name"] = 3
        assert module.dict_getitem_str(d) == 3
        del d["name"]
        raises(KeyError, module.dict_getitem_str, d)
