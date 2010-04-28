from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.pyobject import make_ref, make_typedescr
from pypy.module.cpyext.import_ import PyImport_ImportModule
from pypy.module.cpyext.object import PyObject_GetAttrString
from pypy.module.cpyext.api import generic_cpy_call, cpython_api, bootstrap_function, \
     PyObject, cpython_struct, PyObjectFields, build_type_checkers, CONST_STRING


destructor_short = lltype.Ptr(lltype.FuncType([rffi.VOIDP_real], lltype.Void))
destructor_long = lltype.Ptr(lltype.FuncType([rffi.VOIDP_real, rffi.VOIDP_real], lltype.Void))
PyCObjectStruct = cpython_struct('PyCObject',
                                 PyObjectFields + (
                                     ("cobject", rffi.VOIDP_real),
                                     ("desc", rffi.VOIDP_real),
                                     ("destructor", destructor_short),
                                     ))
PyCObject = lltype.Ptr(PyCObjectStruct)


class W_PyCObject(Wrappable):
    def __init__(self, space):
        self.space = space

W_PyCObject.typedef = TypeDef(
    'PyCObject',
    )
W_PyCObject.typedef.acceptable_as_base_class = False

PyCObject_Check, _ = build_type_checkers("CObject", W_PyCObject)

@bootstrap_function
def init_pycobject(space):
    make_typedescr(W_PyCObject.typedef,
                   basestruct=PyCObjectStruct)

class W_PyCObjectFromVoidPtr(W_PyCObject):
    pyo = lltype.nullptr(PyCObjectStruct)

    def set_pycobject(self, pyo):
        self.pyo = pyo

    def __del__(self):
        pyo = self.pyo
        if pyo and pyo.c_destructor:
            if pyo.c_desc:
                generic_cpy_call(self.space, rffi.cast(destructor_long,
                    pyo.c_destructor), pyo.c_cobject, pyo.c_desc)
            else:
                generic_cpy_call(self.space, pyo.c_destructor, pyo.c_cobject)


@cpython_api([rffi.VOIDP_real, destructor_short], PyObject)
def PyCObject_FromVoidPtr(space, cobj, destr):
    """Create a PyCObject from the void * cobj.  The destr function
    will be called when the object is reclaimed, unless it is NULL."""
    w_pycobject = space.wrap(W_PyCObjectFromVoidPtr(space))
    assert isinstance(w_pycobject, W_PyCObjectFromVoidPtr)
    pyo = make_ref(space, w_pycobject)
    pycobject = rffi.cast(PyCObject, pyo)
    w_pycobject.set_pycobject(pycobject)
    pycobject.c_cobject = cobj
    pycobject.c_destructor = destr
    return pyo

@cpython_api([rffi.VOIDP_real, rffi.VOIDP_real, destructor_long], PyObject)
def PyCObject_FromVoidPtrAndDesc(space, cobj, desc, destr):
    """Create a PyCObject from the void * cobj.  The destr
    function will be called when the object is reclaimed. The desc argument can
    be used to pass extra callback data for the destructor function."""
    w_pycobject = space.wrap(W_PyCObjectFromVoidPtr(space))
    assert isinstance(w_pycobject, W_PyCObjectFromVoidPtr)
    pyo = make_ref(space, w_pycobject)
    pycobject = rffi.cast(PyCObject, pyo)
    w_pycobject.set_pycobject(pycobject)
    pycobject.c_cobject = cobj
    pycobject.c_desc = desc
    pycobject.c_destructor = rffi.cast(destructor_short, destr)
    return pyo

@cpython_api([PyObject], rffi.VOIDP_real, error=lltype.nullptr(rffi.VOIDP_real.TO))
def PyCObject_AsVoidPtr(space, w_obj):
    """Return the object void * that the PyCObject self was
    created with."""
    assert isinstance(w_obj, W_PyCObjectFromVoidPtr)
    return w_obj.pyo.c_cobject

@cpython_api([CONST_STRING, CONST_STRING], rffi.VOIDP_real,
             error=lltype.nullptr(rffi.VOIDP_real.TO))
def PyCObject_Import(space, module_name, name):
    """Return the object void * that the PyCObject self was
    created with."""
    w_mod = PyImport_ImportModule(space, module_name)
    w_obj = PyObject_GetAttrString(space, w_mod, name)
    return PyCObject_AsVoidPtr(space, w_obj)
