from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.pyobject import make_ref
from pypy.module.cpyext.api import generic_cpy_call, cpython_api, PyObject,\
        cpython_struct, PyObjectFields


destructor_short = lltype.Ptr(lltype.FuncType([rffi.VOIDP_real], lltype.Void))
destructor_long = lltype.Ptr(lltype.FuncType([rffi.VOIDP_real, rffi.VOIDP_real], lltype.Void))
PyCObjectStruct = cpython_struct('PyCObject', PyObjectFields + (("destructor", destructor_short), ))
PyCObject = lltype.Ptr(PyCObjectStruct)


class W_PyCObject(Wrappable):
    def __init__(self, space):
        self.space = space

class W_PyCObjectFromVoidPtr(W_PyCObject):
    def __init__(self, space, voidp, desc):
        W_PyCObject.__init__(self, space)
        self.voidp = voidp
        self.pyo = lltype.nullptr(PyCObject.TO)
        self.desc = desc

    def set_pycobject(self, pyo):
        self.pyo = pyo

    def __del__(self):
        if self.pyo and self.pyo.c_destructor:
            if self.desc:
                rffi.cast(self.pyo.c_destructor, destructor_long)(self.pyo, self.desc)
            else:
                self.pyo.c_destructor(self.voidp)


@cpython_api([rffi.VOIDP_real, destructor_short], PyObject)
def PyCObject_FromVoidPtr(space, cobj, destr):
    """Create a PyCObject from the void * cobj.  The destr function
    will be called when the object is reclaimed, unless it is NULL."""
    w_pycobject = space.wrap(W_PyCObjectFromVoidPtr(space, cobj,
        lltype.nullptr(rffi.VOIDP_real.TO)))
    assert isinstance(w_pycobject, W_PyCObjectFromVoidPtr)
    pyo = make_ref(space, w_pycobject)
    pycobject = rffi.cast(PyCObject, pyo)
    w_pycobject.set_pycobject(pycobject)
    pycobject.c_destructor = destr
    return pyo

@cpython_api([rffi.VOIDP_real, rffi.VOIDP_real, destructor_long], PyObject)
def PyCObject_FromVoidPtrAndDesc(space, cobj, desc, destr):
    """Create a PyCObject from the void * cobj.  The destr
    function will be called when the object is reclaimed. The desc argument can
    be used to pass extra callback data for the destructor function."""
    w_pycobject = space.wrap(W_PyCObjectFromVoidPtr(space, cobj,
        desc))
    assert isinstance(w_pycobject, W_PyCObjectFromVoidPtr)
    pyo = make_ref(space, w_pycobject)
    pycobject = rffi.cast(PyCObject, pyo)
    w_pycobject.set_pycobject(pycobject)
    pycobject.c_destructor = rffi.cast(destructor_short, destr)
    return pyo


W_PyCObject.typedef = TypeDef(
    'PyCObject',
    )
W_PyCObject.typedef.acceptable_as_base_class = False


