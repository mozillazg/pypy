from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext import structmemberdefs
from pypy.module.cpyext.api import ADDR, cpython_api
from pypy.module.cpyext.intobject import PyInt_AsLong
from pypy.module.cpyext.pyerrors import PyErr_Occurred
from pypy.module.cpyext.pyobject import PyObject
from pypy.module.cpyext.typeobjectdefs import PyMemberDef


@cpython_api([PyObject, lltype.Ptr(PyMemberDef)], PyObject)
def PyMember_GetOne(space, obj, w_member):
    ptr = rffi.cast(ADDR, obj)
    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    if member_type == structmemberdefs.T_INT:
        result = rffi.cast(rffi.INTP, ptr + w_member.c_offset)
        w_result = space.wrap(result[0])
    else:
        raise OperationError(space.w_SystemError,
                             space.wrap("bad memberdescr type"))
    return w_result


@cpython_api([PyObject, lltype.Ptr(PyMemberDef), PyObject], rffi.INT_real, error=-1)
def PyMember_SetOne(space, obj, w_member, w_value):
    ptr = rffi.cast(ADDR, obj)
    member_type = rffi.cast(lltype.Signed, w_member.c_type)
    if member_type == structmemberdefs.T_INT:
        w_long_value = PyInt_AsLong(space, w_value)
        array = rffi.cast(rffi.INTP, ptr + w_member.c_offset)
        array[0] = rffi.cast(rffi.INT, w_long_value)
    else:
        raise OperationError(space.w_SystemError,
                             space.wrap("bad memberdescr type"))
    return 0
