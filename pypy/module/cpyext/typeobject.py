import sys

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.annlowlevel import llhelper
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import Wrappable
from pypy.objspace.std.typeobject import W_TypeObject, _CPYTYPE
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.cpyext.api import cpython_api, cpython_api_c, cpython_struct, \
    PyObject, PyVarObjectFields, Py_ssize_t, Py_TPFLAGS_READYING, \
    Py_TPFLAGS_READY, Py_TPFLAGS_HEAPTYPE, make_ref, \
    PyStringObject, ADDR, from_ref, generic_cpy_call
from pypy.interpreter.module import Module
from pypy.module.cpyext.modsupport import  convert_method_defs
from pypy.module.cpyext.state import State
from pypy.module.cpyext.methodobject import PyDescr_NewWrapper
from pypy.module.cpyext.macros import Py_INCREF, Py_DECREF, Py_XDECREF
from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr, PyTypeObject, \
        PyGetSetDef
from pypy.module.cpyext.slotdefs import slotdefs


class W_GetSetPropertyEx(GetSetProperty): # XXX fix this to be rpython
    def getter(self, space, w_self):
        return generic_cpy_call(space, self.getset.c_get, w_self, self.getset.c_closure)

    def setter(self, space, w_self, w_value):
        return generic_cpy_call(space, self.getset.c_set, w_self, w_value,
                self.getset.c_closure)

    def __init__(self, getset):
        self.getset = getset
        self.name = rffi.charp2str(getset.c_name)
        doc = set = get = None
        if doc:
            doc = rffi.charp2str(getset.c_doc)
        if getset.c_get:
            get = self.getter.im_func
        if getset.c_set:
            set = self.setter.im_func
        GetSetProperty.__init__(self, get, set, None, doc, W_PyCObject, True)

def PyDescr_NewGetSet(space, getset, pto):
    return space.wrap(W_GetSetPropertyEx(getset))

def convert_getset_defs(space, dict_w, getsets, pto):
    getsets = rffi.cast(rffi.CArrayPtr(PyGetSetDef), getsets)
    if getsets:
        i = -1
        while True:
            i = i + 1
            getset = getsets[i]
            name = getset.c_name
            if not name:
                break
            name = rffi.charp2str(name)
            w_descr = PyDescr_NewGetSet(space, getset, pto)
            dict_w[name] = w_descr

def add_operators(space, dict_w, pto):
    # XXX support PyObject_HashNotImplemented
    state = space.fromcache(State)
    for method_name, slot_name, _, wrapper_func, wrapper_func_kwds, doc in state.slotdefs: # XXX use UI
        if method_name in dict_w:
            continue
        # XXX is this rpython?
        if len(slot_name) == 1:
            func = getattr(pto, slot_name[0])
        else:
            assert len(slot_name) == 2
            struct = getattr(pto, slot_name[0])
            if not struct:
                continue
            func = getattr(struct, slot_name[1])
        func_voidp = rffi.cast(rffi.VOIDP_real, func)
        if not func:
            continue
        if wrapper_func is None and wrapper_func_kwds is None:
            print >>sys.stderr, method_name, "used by the type but no wrapper function defined!"
            continue
        dict_w[method_name] = PyDescr_NewWrapper(space, pto, method_name, wrapper_func,
                wrapper_func_kwds, doc, func_voidp)


class W_PyCTypeObject(W_TypeObject):
    def __init__(self, space, pto):
        self.pto = pto
        bases_w = []
        dict_w = {}

        add_operators(space, dict_w, pto)
        convert_method_defs(space, dict_w, pto.c_tp_methods, pto)
        convert_getset_defs(space, dict_w, pto.c_tp_getset, pto)
        # XXX missing: convert_member_defs

        full_name = rffi.charp2str(pto.c_tp_name)
        module_name, extension_name = full_name.split(".", 1)
        dict_w["__module__"] = space.wrap(module_name)

        W_TypeObject.__init__(self, space, extension_name,
            bases_w or [space.w_object], dict_w)
        self.__flags__ = _CPYTYPE # mainly disables lookup optimizations

class W_PyCObject(Wrappable):
    def __init__(self, space):
        self.space = space


@cpython_api([PyObject], lltype.Void, external=False)
def subtype_dealloc(space, obj):
    pto = rffi.cast(PyTypeObjectPtr, obj.c_ob_type)
    assert pto.c_tp_flags & Py_TPFLAGS_HEAPTYPE
    base = pto
    this_func_ptr = subtype_dealloc.api_func.get_llhelper(space)
    ref_of_object_type = rffi.cast(PyTypeObjectPtr,
            make_ref(space, space.w_object, steal=True))
    while base.c_tp_dealloc == this_func_ptr:
        base = base.c_tp_base
        assert base
    dealloc = base.c_tp_dealloc
    # XXX call tp_del if necessary
    generic_cpy_call(space, dealloc, obj)
    pto = rffi.cast(PyObject, pto)
    Py_DECREF(space, pto)


@cpython_api([PyObject], lltype.Void, external=False)
def string_dealloc(space, obj):
    obj = rffi.cast(PyStringObject, obj)
    pto = rffi.cast(PyTypeObjectPtr, obj.c_ob_type)
    if obj.c_buffer:
        lltype.free(obj.c_buffer, flavor="raw")
    obj_voidp = rffi.cast(rffi.VOIDP_real, obj)
    generic_cpy_call(space, pto.c_tp_free, obj_voidp)
    pto = rffi.cast(PyObject, pto)
    Py_DECREF(space, pto)

@cpython_api([PyObject], lltype.Void, external=False)
def type_dealloc(space, obj):
    state = space.fromcache(State)
    obj_pto = rffi.cast(PyTypeObjectPtr, obj)
    type_pto = rffi.cast(PyTypeObjectPtr, obj.c_ob_type)
    base_pyo = rffi.cast(PyObject, obj_pto.c_tp_base)
    Py_XDECREF(space, base_pyo)
    Py_XDECREF(space, obj_pto.c_tp_bases)
    Py_XDECREF(space, obj_pto.c_tp_cache) # lets do it like cpython
    if obj_pto.c_tp_flags & Py_TPFLAGS_HEAPTYPE:
        lltype.free(obj_pto.c_tp_name, flavor="raw")
        obj_pto_voidp = rffi.cast(rffi.VOIDP_real, obj_pto)
        generic_cpy_call(space, type_pto.c_tp_free, obj_pto_voidp)
        pto = rffi.cast(PyObject, type_pto)
        Py_DECREF(space, pto)


def allocate_type_obj(space, w_type):
    """ Allocates a pto from a w_type which must be a PyPy type. """
    state = space.fromcache(State)
    from pypy.module.cpyext.object import PyObject_dealloc, PyObject_Del
    assert not isinstance(w_type, W_PyCTypeObject)
    assert isinstance(w_type, W_TypeObject)

    pto = lltype.malloc(PyTypeObject, None, flavor="raw", zero=True)
    pto.c_ob_refcnt = 1
    # put the type object early into the dict
    # to support dependency cycles like object/type
    state = space.fromcache(State)
    state.py_objects_w2r[w_type] = rffi.cast(PyObject, pto)

    if space.is_w(w_type, space.w_object):
        pto.c_tp_dealloc = PyObject_dealloc.api_func.get_llhelper(space)
    elif space.is_w(w_type, space.w_type):
        pto.c_tp_dealloc = type_dealloc.api_func.get_llhelper(space)
    elif space.is_w(w_type, space.w_str):
        pto.c_tp_dealloc = string_dealloc.api_func.get_llhelper(space)
    else:
        pto.c_tp_dealloc = subtype_dealloc.api_func.get_llhelper(space)
    pto.c_tp_flags = Py_TPFLAGS_HEAPTYPE
    pto.c_tp_free = PyObject_Del.api_func.get_llhelper(space)
    pto.c_tp_name = rffi.str2charp(w_type.getname(space, "?"))
    pto.c_tp_basicsize = -1 # hopefully this makes malloc bail out
    pto.c_tp_itemsize = 0
    # uninitialized fields:
    # c_tp_print, c_tp_getattr, c_tp_setattr
    # XXX implement
    # c_tp_compare and the following fields (see http://docs.python.org/c-api/typeobj.html )
    bases_w = w_type.bases_w
    assert len(bases_w) <= 1
    pto.c_tp_base = lltype.nullptr(PyTypeObject)
    pto.c_tp_bases = lltype.nullptr(PyObject.TO)
    if not space.is_w(w_type, space.w_type) and not \
            space.is_w(w_type, space.w_object):
        if bases_w:
            ref = make_ref(space, bases_w[0])
            pto.c_tp_base = rffi.cast(PyTypeObjectPtr, ref)
        pto.c_ob_type = make_ref(space, space.type(space.w_type))
        PyPyType_Ready(space, pto, w_type)
    else:
        pto.c_ob_type = lltype.nullptr(PyObject.TO)

    #  XXX fill slots in pto
    #  would look like fixup_slot_dispatchers()
    return pto

@cpython_api([PyTypeObjectPtr], rffi.INT_real, error=-1)
def PyType_Ready(space, pto):
    return PyPyType_Ready(space, pto, None)

def PyPyType_Ready(space, pto, w_obj):
    try:
        pto.c_tp_dict = lltype.nullptr(PyObject.TO) # not supported
        if pto.c_tp_flags & Py_TPFLAGS_READY:
            return 0
        assert pto.c_tp_flags & Py_TPFLAGS_READYING == 0
        pto.c_tp_flags |= Py_TPFLAGS_READYING
        base = pto.c_tp_base
        if not base and not (w_obj is not None and
            space.is_w(w_obj, space.w_object)):
            base_pyo = make_ref(space, space.w_object)
            base = pto.c_tp_base = rffi.cast(PyTypeObjectPtr, base_pyo)
        if base and not base.c_tp_flags & Py_TPFLAGS_READY:
            PyPyType_Ready(space, base, None)
        if base and not pto.c_ob_type: # will be filled later
            pto.c_ob_type = base.c_ob_type
        if not pto.c_tp_bases and not (space.is_w(w_obj, space.w_object)
                or space.is_w(w_obj, space.w_type)):
            if not base:
                bases = space.newtuple([])
            else:
                bases = space.newtuple([from_ref(space, base)])
            pto.c_tp_bases = make_ref(space, bases)
        if w_obj is None:
            PyPyType_Register(space, pto)
        # missing:
        # inherit_special, inherit_slots, setting __doc__ if not defined and tp_doc defined
        # inheriting tp_as_* slots
        # unsupported:
        # tp_mro, tp_subclasses
    finally:
        pto.c_tp_flags &= ~Py_TPFLAGS_READYING
    pto.c_tp_flags = (pto.c_tp_flags & ~Py_TPFLAGS_READYING) | Py_TPFLAGS_READY
    return 0

def PyPyType_Register(space, pto):
    state = space.fromcache(State)
    ptr = rffi.cast(ADDR, pto)
    if ptr not in state.py_objects_r2w:
        w_obj = space.allocate_instance(W_PyCTypeObject,
                space.gettypeobject(W_PyCTypeObject.typedef))
        state.non_heaptypes.append(w_obj)
        pyo = rffi.cast(PyObject, pto)
        state.py_objects_r2w[ptr] = w_obj
        state.py_objects_w2r[w_obj] = pyo
        w_obj.__init__(space, pto)
        w_obj.ready()
    return 1

W_PyCObject.typedef = W_ObjectObject.typedef

W_PyCTypeObject.typedef = TypeDef(
    'C_type', W_TypeObject.typedef
    )
