from rpython.rtyper.lltypesystem import lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pyobject import PyObjectP, as_pyobj
from pypy.module.cpyext.pyobject import get_w_obj_and_decref
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class TestIterator(BaseApiTest):
    def test_check(self, space, api):
        assert api.PyIndex_Check(space.wrap(12))
        assert api.PyIndex_Check(space.wraplong(-12L))
        assert not api.PyIndex_Check(space.wrap(12.1))
        assert not api.PyIndex_Check(space.wrap('12'))

        assert api.PyNumber_Check(space.wrap(12))
        assert api.PyNumber_Check(space.wraplong(-12L))
        assert api.PyNumber_Check(space.wrap(12.1))
        assert not api.PyNumber_Check(space.wrap('12'))
        assert not api.PyNumber_Check(space.wrap(1+3j))

    def test_number_long(self, space, api):
        w_l = api.PyNumber_Long(space.wrap(123))
        assert api.PyLong_CheckExact(w_l)
        w_l = api.PyNumber_Long(space.wrap("123"))
        assert api.PyLong_CheckExact(w_l)

    def test_number_int(self, space, api):
        w_l = api.PyNumber_Int(space.wraplong(123L))
        assert api.PyInt_CheckExact(w_l)
        w_l = api.PyNumber_Int(space.wrap(2 << 65))
        assert api.PyLong_CheckExact(w_l)
        w_l = api.PyNumber_Int(space.wrap(42.3))
        assert api.PyInt_CheckExact(w_l)
        w_l = api.PyNumber_Int(space.wrap("42"))
        assert api.PyInt_CheckExact(w_l)

    def test_number_index(self, space, api):
        w_l = api.PyNumber_Index(space.wraplong(123L))
        assert api.PyLong_CheckExact(w_l)
        w_l = api.PyNumber_Index(space.wrap(42.3))
        assert w_l is None
        api.PyErr_Clear()

    def test_coerce(self, space, api):
        w_obj1 = space.wrap(123)
        w_obj2 = space.wrap(456.789)
        pp1 = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        pp1[0] = as_pyobj(space, w_obj1)
        pp2 = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        pp2[0] = as_pyobj(space, w_obj2)
        assert api.PyNumber_Coerce(pp1, pp2) == 0
        w_res1 = get_w_obj_and_decref(space, pp1[0])
        w_res2 = get_w_obj_and_decref(space, pp2[0])
        lltype.free(pp1, flavor='raw')
        lltype.free(pp2, flavor='raw')
        assert space.str_w(space.repr(w_res1)) == '123.0'
        assert space.str_w(space.repr(w_res2)) == '456.789'

    def test_number_coerce_ex(self, space, api):
        w_objl = space.wrap(123)
        w_objf = space.wrap(42.5)
        ppl = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ppf = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ppl[0] = as_pyobj(space, w_objl)
        ppf[0] = as_pyobj(space, w_objf)

        ret = api.PyNumber_CoerceEx(ppl, ppf)
        assert ret == 0

        w_resl = get_w_obj_and_decref(space, ppl[0])
        w_resf = get_w_obj_and_decref(space, ppf[0])
        lltype.free(ppl, flavor='raw')
        lltype.free(ppf, flavor='raw')

        assert api.PyFloat_Check(w_resl)
        assert space.unwrap(w_resl) == 123.
        assert isinstance(space.unwrap(w_resl), float)
        assert space.unwrap(w_resf) == 42.5

    def test_numbermethods(self, space, api):
        assert "ab" == space.unwrap(
            api.PyNumber_Add(space.wrap("a"), space.wrap("b")))
        assert "aaa" == space.unwrap(
            api.PyNumber_Multiply(space.wrap("a"), space.wrap(3)))

        w_l = space.newlist([1, 2, 3])
        w_l2 = api.PyNumber_Multiply(w_l, space.wrap(3))
        assert api.PyObject_Size(w_l2) == 9
        assert api.PyObject_Size(w_l) == 3

        w_l3 = api.PyNumber_InPlaceMultiply(w_l, space.wrap(3))
        assert api.PyObject_Size(w_l) == 9
        assert w_l3 is w_l

        # unary function
        assert 9 == space.unwrap(api.PyNumber_Absolute(space.wrap(-9)))

        # power
        assert 9 == space.unwrap(
            api.PyNumber_Power(space.wrap(3), space.wrap(2), space.w_None))
        assert 4 == space.unwrap(
            api.PyNumber_Power(space.wrap(3), space.wrap(2), space.wrap(5)))
        assert 9 == space.unwrap(
            api.PyNumber_InPlacePower(space.wrap(3), space.wrap(2), space.w_None))

class AppTestCNumber(AppTestCpythonExtensionBase):
    def test_app_coerce(self):
        mod = self.import_extension('foo', [
            ("test_fail", "METH_NOARGS",
             '''
                PyObject * hello = PyString_FromString("hello");
                PyObject * float1 = PyFloat_FromDouble(1.0);
                int retVal = PyNumber_Coerce(&hello, &float1);
                Py_DECREF(hello);
                Py_DECREF(float1);
                return PyInt_FromLong(retVal);
            '''),
            ("test", "METH_NOARGS",
             '''
                PyObject * float1p = PyFloat_FromDouble(1.0);
                PyObject * int3p   = PyInt_FromLong(3);
                PyObject * tupl = PyTuple_New(2);
                PyObject float1 = *float1p;
                PyObject int3 = *int3p;
                int retVal = PyNumber_CoerceEx(&int3p, &float1p);
                if (retVal == 0)
                {
                    PyTuple_SET_ITEM(tupl, 0, int3p);
                    PyTuple_SET_ITEM(tupl, 1, float1p);
                }
                Py_DECREF(&int3);
                Py_DECREF(&float1);
                Py_DECREF(int3p);
                Py_DECREF(float1p);
                return tupl;
            ''')])
        assert mod.test_fail() == -1
        '''tupl = mod.test()
        assert tupl[0] == 3.
        assert tupl[1] == 1.
        assert isinstance(tupl[0], float)'''
