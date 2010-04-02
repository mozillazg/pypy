from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

#class TestObject(BaseApiTest):
#    def test_Size(self, space, api):
#        s = space.wrap("test")
#        assert api.PyString_Size(s) == 4

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
              va_start(va, fmt);
              PyObject* res = PyString_FromFormatV(fmt, va);
              va_end(va);
              return res;
            }
            ''')
        res = module.test_string_format_v(1, "xyz")
        print res
