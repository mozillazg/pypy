from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, PyObject, CANNOT_FAIL, \
     VA_LIST_P, register_c_function
from pypy.module.cpyext import api
from pypy.module.cpyext.pyobject import from_ref, make_ref,\
     add_borrowed_object, register_container
from pypy.rpython.lltypesystem import lltype, rffi

for name in ['PyArg_Parse', 'PyArg_ParseTuple', 'PyArg_UnpackTuple',
             'PyArg_ParseTupleAndKeywords']:
    register_c_function(name)
