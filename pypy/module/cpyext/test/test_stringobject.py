from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.stringobject import new_empty_str
from pypy.module.cpyext.api import PyStringObject, PyObjectP, PyObject
from pypy.module.cpyext.pyobject import Py_DecRef

import py
import sys

class AppTestStringObject(AppTestCpythonExtensionBase):
    def test_stringobject(self):
        module = self.import_extension('foo', [
            ("get_hello1", "METH_NOARGS",
             """
                 return PyString_FromStringAndSize(
                     "Hello world<should not be included>", 11);
             """),
            ("get_hello2", "METH_NOARGS",
             """
                 return PyString_FromString("Hello world");
             """),
            ("test_Size", "METH_NOARGS",
             """
                 PyObject* s = PyString_FromString("Hello world");
                 int result = 0;

                 if(PyString_Size(s) == 11) {
                     result = 1;
                 }
                 Py_DECREF(s);
                 return PyBool_FromLong(result);
             """),
            ("test_Size_exception", "METH_NOARGS",
             """
                 PyObject* f = PyFloat_FromDouble(1.0);
                 Py_ssize_t size = PyString_Size(f);

                 Py_DECREF(f);
                 return NULL;
             """),
             ("test_is_string", "METH_VARARGS",
             """
                return PyBool_FromLong(PyString_Check(PyTuple_GetItem(args, 0)));
             """)])
        assert module.get_hello1() == 'Hello world'
        assert module.get_hello2() == 'Hello world'
        assert module.test_Size()
        raises(TypeError, module.test_Size_exception)
    
        assert module.test_is_string("")
        assert not module.test_is_string(())

    def test_string_buffer_init(self):
        module = self.import_extension('foo', [
            ("getstring", "METH_NOARGS",
             """
                 PyObject *s, *t;
                 char* c;
                 Py_ssize_t len;

                 s = PyString_FromStringAndSize(NULL, 3);
                 if (s == NULL)
                    return NULL;
                 t = PyString_FromStringAndSize(NULL, 3);
                 if (t == NULL)
                    return NULL;
                 Py_DECREF(t);
                 c = PyString_AsString(s);
                 //len = PyString_Size(s);
                 c[0] = 'a';
                 c[1] = 'b'; 
                 c[2] = 'c';//len-1] = 'c';
                 return s;
             """),
            ])
        s = module.getstring()
        assert len(s) == 3
        assert s == 'abc'



    def test_AsString(self):
        module = self.import_extension('foo', [
            ("getstring", "METH_NOARGS",
             """
                 PyObject* s1 = PyString_FromStringAndSize("test", 4);
                 char* c = PyString_AsString(s1);
                 PyObject* s2 = PyString_FromStringAndSize(c, 4);
                 Py_DECREF(s1);
                 return s2;
             """),
            ])
        s = module.getstring()
        assert s == 'test'

    def test_py_string_as_string(self):
        module = self.import_extension('foo', [
            ("string_as_string", "METH_VARARGS",
             '''
             return PyString_FromStringAndSize(PyString_AsString(
                       PyTuple_GetItem(args, 0)), 4);
             '''
            )])
        assert module.string_as_string("huheduwe") == "huhe"

    def test_format_v(self):
        module = self.import_extension('foo', [
            ("test_string_format_v", "METH_VARARGS",
             '''
                 return helper("bla %d ble %s\\n",
                        PyInt_AsLong(PyTuple_GetItem(args, 0)),
                        PyString_AsString(PyTuple_GetItem(args, 1)));
             '''
             )
            ], prologue='''
            PyObject* helper(char* fmt, ...)
            {
              va_list va;
              PyObject* res;
              va_start(va, fmt);
              res = PyString_FromFormatV(fmt, va);
              va_end(va);
              return res;
            }
            ''')
        res = module.test_string_format_v(1, "xyz")
        assert res == "bla 1 ble xyz\n"
        
    def test_format(self):
        module = self.import_extension('foo', [
            ("test_string_format", "METH_VARARGS",
             '''
                 return PyString_FromFormat("bla %d ble %s\\n",
                        PyInt_AsLong(PyTuple_GetItem(args, 0)),
                        PyString_AsString(PyTuple_GetItem(args, 1)));
             '''
             )
            ])
        res = module.test_string_format(1, "xyz")
        assert res == "bla 1 ble xyz\n"

class TestString(BaseApiTest):
    def test_string_resize(self, space, api):
        py_str = new_empty_str(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        py_str.c_buffer[0] = 'a'
        py_str.c_buffer[1] = 'b'
        py_str.c_buffer[2] = 'c'
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyString_Resize(ar, 3)
        py_str = rffi.cast(PyStringObject, ar[0])
        assert py_str.c_size == 3
        assert py_str.c_buffer[1] == 'b'
        assert py_str.c_buffer[3] == '\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyString_Resize(ar, 10)
        py_str = rffi.cast(PyStringObject, ar[0])
        assert py_str.c_size == 10
        assert py_str.c_buffer[1] == 'b'
        assert py_str.c_buffer[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

    def test_string_buffer(self, space, api):
        py_str = new_empty_str(space, 10)
        c_buf = py_str.c_ob_type.c_tp_as_buffer
        assert c_buf
        py_obj = rffi.cast(PyObject, py_str)
        assert c_buf.c_bf_getsegcount(py_obj, lltype.nullptr(rffi.INTP.TO)) == 1
        ref = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
        assert c_buf.c_bf_getsegcount(py_obj, ref) == 1
        assert ref[0] == 10
        lltype.free(ref, flavor='raw')
        ref = lltype.malloc(rffi.VOIDPP.TO, 1, flavor='raw')
        assert c_buf.c_bf_getreadbuffer(py_obj, 0, ref) == 10
        lltype.free(ref, flavor='raw')
        Py_DecRef(space, py_obj)
