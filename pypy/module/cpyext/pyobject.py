import sys

from pypy.interpreter.baseobjspace import W_Root, SpaceCache
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.extregistry import ExtRegistryEntry
from pypy.module.cpyext.api import (
    cpython_api, bootstrap_function, PyObject, PyObjectP, ADDR,
    CANNOT_FAIL, Py_TPFLAGS_HEAPTYPE, PyTypeObjectPtr, is_PyObject,
    INTERPLEVEL_API)
from pypy.module.cpyext.state import State
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.std.objectobject import W_ObjectObject
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib import rawrefcount


#________________________________________________________
# type description

def make_typedescr(arg0, *args, **kwds):
    print "ZZZ: make_typedescr(%r)" % (arg0,)
def get_typedescr(*args, **kwds):
    ZZZ
RefcountState = "ZZZ"

RRC_PERMANENT       = 'P'  # the link pyobj<->pypy is permanent
RRC_PERMANENT_LIGHT = 'p'  # same, but tp_dealloc can be replaced with free()
RRC_TRANSIENT       = 'T'  # the pypy object is transient and can go away
RRC_TRANSIENT_LIGHT = 't'  # same, but tp_dealloc can be replaced with free()

def setup_class_for_cpyext(W_Class, **kw):
    """NOT_RPYTHON

    basestruct: The basic structure to allocate
    alloc_pyobj: function called to get the PyObject
    fill_pyobj: called to fill the PyObject after attaching is done
    alloc_pypy: function called to create a PyPy object from a PyObject
    fill_pypy: called to fill the PyPy object after attaching is done
    dealloc: function called with the pyobj when the refcount drops to zero
    """

    tp_basestruct = kw.pop('basestruct', PyObject.TO)
    tp_alloc_pyobj  = kw.pop('alloc_pyobj', None)
    tp_fill_pyobj   = kw.pop('fill_pyobj', None)
    tp_alloc_pypy   = kw.pop('alloc_pypy', None)
    tp_fill_pypy    = kw.pop('fill_pypy', None)
    tp_dealloc      = kw.pop('dealloc', None)
    force_create_pyobj  = kw.pop('force_create_pyobj', False)
    realize_subclass_of = kw.pop('realize_subclass_of', None)
    alloc_pypy_light_if = kw.pop('alloc_pypy_light_if', None)
    assert not kw, "Extra arguments to setup_class_for_cpyext: %s" % kw.keys()

    assert 'cpyext_basestruct' not in W_Class.__dict__    # double set

    if tp_alloc_pyobj or tp_fill_pyobj or force_create_pyobj:
        #
        if not tp_alloc_pyobj:
            def tp_alloc_pyobj(space, w_obj):
                ob = lltype.malloc(tp_basestruct, flavor='raw',
                                   track_allocation=False)
                return ob, RRC_PERMANENT_LIGHT
        tp_alloc_pyobj._always_inline_ = True
        #
        if not tp_fill_pyobj:
            def tp_fill_pyobj(space, w_obj, py_obj):
                pass
        #
        def cpyext_create_pyobj(self, space):
            py_obj, strength = tp_alloc_pyobj(space, self)
            ob = rffi.cast(PyObject, py_obj)
            ob.c_ob_refcnt = 0
            ob.c_ob_type = get_c_ob_type(space, space.type(self))
            rawrefcount_init_link(self, ob, strength)
            tp_fill_pyobj(space, self, py_obj)
            return ob
        W_Class.cpyext_create_pyobj = cpyext_create_pyobj
        #
        def cpyext_fill_prebuilt_pyobj(self, space):
            ob_type = get_c_ob_type(space, space.type(self))
            py_obj = as_pyobj(space, self)
            py_obj.c_ob_type = ob_type
            ob = rffi.cast(lltype.Ptr(tp_basestruct), py_obj)
            tp_fill_pyobj(space, self, ob)
            keepalive_until_here(self)
        W_Class.cpyext_fill_prebuilt_pyobj = cpyext_fill_prebuilt_pyobj

    if tp_alloc_pyobj or tp_fill_pyobj or realize_subclass_of or tp_dealloc:
        if realize_subclass_of is None:
            realize_subclass_of = W_Class
        #
        if not tp_alloc_pypy:
            W_CPyExtPlaceHolder = get_cpyextplaceholder_subclass(
                realize_subclass_of)
            def tp_alloc_pypy(space, pyobj):
                w_obj = W_CPyExtPlaceHolder(pyobj)
                strength = RRC_TRANSIENT
                if alloc_pypy_light_if is not None:
                    if alloc_pypy_light_if(space, pyobj):
                        strength = RRC_TRANSIENT_LIGHT
                return w_obj, strength
        tp_alloc_pypy._always_inline_ = True
        #
        if not tp_fill_pypy:
            def tp_fill_pypy(space, w_obj, pyobj):
                pass
        #
        def cpyext_create_pypy(space, pyobj):
            w_obj, strength = tp_alloc_pypy(space, pyobj)
            rawrefcount_init_link(w_obj, pyobj, strength)
            tp_fill_pypy(space, w_obj, pyobj)
            return w_obj
        #
        typedef = realize_subclass_of.typedef
        assert 'cpyext_create_pypy' not in typedef.__dict__
        typedef.cpyext_create_pypy = cpyext_create_pypy

        if tp_basestruct._arrayfld is None:
            typedef.cpyext_basicsize = rffi.sizeof(tp_basestruct)
            typedef.cpyext_itemsize = 0
        else:
            typedef.cpyext_basicsize = rffi.offsetof(tp_basestruct,
                                                     tp_basestruct._arrayfld)
            ARRAY = getattr(tp_basestruct, tp_basestruct._arrayfld)
            typedef.cpyext_itemsize = rffi.sizeof(ARRAY.OF)

        if tp_dealloc:
            @cpython_api([PyObject], lltype.Void,
                         external=False, error=CANNOT_FAIL)
            def dealloc(space, py_obj):
                tp_dealloc(space, rffi.cast(lltype.Ptr(tp_basestruct), py_obj))
            #
            def cpyext_get_dealloc(space):
                return llhelper(dealloc.api_func.functype,
                                dealloc.api_func.get_wrapper(space))
            #
            assert 'cpyext_get_dealloc' not in typedef.__dict__
            typedef.cpyext_get_dealloc = cpyext_get_dealloc

    W_Class.cpyext_basestruct = tp_basestruct


def rawrefcount_init_link(w_obj, ob, strength):
    assert lltype.typeOf(ob) == PyObject
    if strength == RRC_PERMANENT:
        ob.c_ob_refcnt += rawrefcount.REFCNT_FROM_PYPY
        rawrefcount.create_link_pypy(w_obj, ob)
    #
    elif strength == RRC_PERMANENT_LIGHT:
        ob.c_ob_refcnt += rawrefcount.REFCNT_FROM_PYPY_LIGHT
        rawrefcount.create_link_pypy(w_obj, ob)
    #
    elif strength == RRC_TRANSIENT:
        ob.c_ob_refcnt += rawrefcount.REFCNT_FROM_PYPY
        rawrefcount.create_link_pyobj(w_obj, ob)
    #
    elif strength == RRC_TRANSIENT_LIGHT:
        ob.c_ob_refcnt += rawrefcount.REFCNT_FROM_PYPY_LIGHT
        rawrefcount.create_link_pyobj(w_obj, ob)
    #
    else:
        assert False, "rawrefcount_init_link: strength=%r" % (strength,)


def setup_prebuilt_pyobj(w_obj, py_obj):
    rawrefcount_init_link(w_obj, py_obj, RRC_PERMANENT)
    if isinstance(w_obj, W_TypeObject):
        w_obj.cpyext_c_type_object = rffi.cast(PyTypeObjectPtr, py_obj)

def get_c_ob_type(space, w_type):
    pto = w_type.cpyext_c_type_object
    if not pto:
        ob = w_type.cpyext_create_pyobj(space)
        pto = rffi.cast(PyTypeObjectPtr, ob)
    return pto
W_TypeObject.cpyext_c_type_object = lltype.nullptr(PyTypeObjectPtr.TO)

@bootstrap_function
def init_pyobject(space):
    setup_class_for_cpyext(W_Root, force_create_pyobj=True,
                           realize_subclass_of=W_ObjectObject,
                           dealloc=_default_dealloc)
    # use this cpyext_create_pypy as the default for all other TypeDefs
    from pypy.interpreter.typedef import TypeDef
    TypeDef.cpyext_create_pypy = staticmethod(
        W_ObjectObject.typedef.cpyext_create_pypy)
    TypeDef.cpyext_get_dealloc = staticmethod(
        W_ObjectObject.typedef.cpyext_get_dealloc)
    TypeDef.cpyext_basicsize = W_ObjectObject.typedef.cpyext_basicsize
    TypeDef.cpyext_itemsize = W_ObjectObject.typedef.cpyext_itemsize

def _default_dealloc(space, py_obj):
    lltype.free(py_obj, flavor='raw', track_allocation=False)


#________________________________________________________
# W_CPyExtPlaceHolderObject

# When we ask for the convertion of a PyObject to a W_Root and there
# is none, we look up the correct W_Root subclass to use (W_IntObject,
# etc., or W_ObjectObject by default), take the W_CPyExtPlaceHolder
# special subclass of it, and instantiate that.  W_CPyExtPlaceHolder
# adds the field "cpyext_pyobj" pointing back to the PyObject.
# W_CPyExtPlaceHolder is made using the following memo function.

@specialize.memo()
def get_cpyextplaceholder_subclass(W_Class):
    try:
        return W_Class.__dict__['_cpyextplaceholder_subclass']
    except KeyError:
        pass
    assert W_Class is not W_TypeObject

    class W_CPyExtPlaceHolder(W_Class):
        def __init__(self, pyobj):
            self.cpyext_pyobj = pyobj
        def cpyext_as_pyobj(self, space):
            return self.cpyext_pyobj

        def getclass(self, space):
            w_type = from_pyobj(space, self.cpyext_pyobj.c_ob_type)
            assert isinstance(w_type, W_TypeObject)
            return w_type

        # ZZZ getclass(), getweakref(), etc.?  like interpreter/typedef.py

    W_CPyExtPlaceHolder.__name__ = W_Class.__name__ + '_CPyExtPlaceHolder'
    W_Class._cpyextplaceholder_subclass = W_CPyExtPlaceHolder
    return W_CPyExtPlaceHolder



def _default_cpyext_as_pyobj(self, space):
    """Default implementation for most classes in PyPy.
    Overridden by the W_CPyExtPlaceHolder subclasses."""
    ob = rawrefcount.from_obj(PyObject, self)
    if not ob:
        ob = self.cpyext_create_pyobj(space)
    return ob
W_Root.cpyext_as_pyobj = _default_cpyext_as_pyobj

def _type_cpyext_as_pyobj(self, space):
    ob = get_c_ob_type(space, self)
    return rffi.cast(PyObject, ob)
W_TypeObject.cpyext_as_pyobj = _type_cpyext_as_pyobj
W_TypeObject._cpyextplaceholder_subclass = W_TypeObject

def _create_w_obj_from_pyobj(space, pyobj):
    w_type = from_pyobj(space, pyobj.c_ob_type)
    assert isinstance(w_type, W_TypeObject)
    return w_type.instancetypedef.cpyext_create_pypy(space, pyobj)

#________________________________________________________
# refcounted object support

DEBUG_REFCOUNT = False

def debug_refcount(*args, **kwargs):
    frame_stackdepth = kwargs.pop("frame_stackdepth", 2)
    assert not kwargs
    frame = sys._getframe(frame_stackdepth)
    print >>sys.stderr, "%25s" % (frame.f_code.co_name, ),
    for arg in args:
        print >>sys.stderr, arg,
    print >>sys.stderr

def create_ref(space, w_obj, itemcount=0):
    """
    Allocates a PyObject, and fills its fields with info from the given
    intepreter object.
    """
    ZZZ
    state = space.fromcache(RefcountState)
    w_type = space.type(w_obj)
    if w_type.is_cpytype():
        py_obj = state.get_from_lifeline(w_obj)
        if py_obj:
            Py_IncRef(space, py_obj)
            return py_obj

    typedescr = get_typedescr(w_obj.typedef)
    py_obj = typedescr.allocate(space, w_type, itemcount=itemcount)
    if w_type.is_cpytype():
        state.set_lifeline(w_obj, py_obj)
    typedescr.attach(space, py_obj, w_obj)
    return py_obj

def track_reference(space, py_obj, w_obj, replace=False):
    """
    Ties together a PyObject and an interpreter object.
    """
    ZZZ
    # XXX looks like a PyObject_GC_TRACK
    ptr = rffi.cast(ADDR, py_obj)
    state = space.fromcache(RefcountState)
    if DEBUG_REFCOUNT:
        debug_refcount("MAKREF", py_obj, w_obj)
        if not replace:
            assert w_obj not in state.py_objects_w2r
        assert ptr not in state.py_objects_r2w
    state.py_objects_w2r[w_obj] = py_obj
    if ptr: # init_typeobject() bootstraps with NULL references
        state.py_objects_r2w[ptr] = w_obj


def debug_collect():
    rawrefcount._collect(track_allocation=False)


def as_pyobj(space, w_obj):
    """
    Returns a 'PyObject *' representing the given intepreter object.
    This doesn't give a new reference, but the returned 'PyObject *'
    is valid at least as long as 'w_obj' is.  To be safe, you should
    use keepalive_until_here(w_obj) some time later.
    """
    assert not is_pyobj(w_obj)
    return w_obj.cpyext_as_pyobj(space)
as_pyobj._always_inline_ = True
INTERPLEVEL_API['as_pyobj'] = as_pyobj

def as_xpyobj(space, w_obj):
    if w_obj is not None:
        return as_pyobj(space, w_obj)
    else:
        return lltype.nullptr(PyObject.TO)
INTERPLEVEL_API['as_xpyobj'] = as_xpyobj


def pyobj_has_w_obj(pyobj):
    return rawrefcount.to_obj(W_Root, pyobj) is not None
INTERPLEVEL_API['pyobj_has_w_obj'] = staticmethod(pyobj_has_w_obj)

@specialize.ll()
def from_pyobj(space, pyobj):
    assert is_pyobj(pyobj)
    assert pyobj
    pyobj = rffi.cast(PyObject, pyobj)
    w_obj = rawrefcount.to_obj(W_Root, pyobj)
    if w_obj is None:
        w_obj = _create_w_obj_from_pyobj(space, pyobj)
    return w_obj
from_pyobj._always_inline_ = True
INTERPLEVEL_API['from_pyobj'] = from_pyobj

@specialize.ll()
def from_xpyobj(space, pyobj):
    if pyobj:
        return from_pyobj(space, pyobj)
    else:
        return None
INTERPLEVEL_API['from_xpyobj'] = from_xpyobj


def is_pyobj(x):
    if x is None or isinstance(x, W_Root):
        return False
    elif is_PyObject(lltype.typeOf(x)):
        return True
    else:
        raise TypeError(repr(type(x)))
INTERPLEVEL_API['is_pyobj'] = staticmethod(is_pyobj)

class Entry(ExtRegistryEntry):
    _about_ = is_pyobj
    def compute_result_annotation(self, s_x):
        from rpython.rtyper.llannotation import SomePtr
        return self.bookkeeper.immutablevalue(isinstance(s_x, SomePtr))
    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Bool, hop.s_result.const)


@specialize.ll()
def get_pyobj_and_incref(space, obj):
    """Increment the reference counter of the PyObject and return it.
    Can be called with either a PyObject or a W_Root.
    """
    if is_pyobj(obj):
        pyobj = rffi.cast(PyObject, obj)
    else:
        pyobj = as_pyobj(space, obj)
    assert pyobj.c_ob_refcnt > 0
    pyobj.c_ob_refcnt += 1
    if not is_pyobj(obj):
        keepalive_until_here(obj)
    return pyobj
INTERPLEVEL_API['get_pyobj_and_incref'] = get_pyobj_and_incref

@specialize.ll()
def get_pyobj_and_xincref(space, obj):
    if obj:
        return get_pyobj_and_incref(space, obj)
    else:
        return lltype.nullptr(PyObject.TO)
INTERPLEVEL_API['get_pyobj_and_xincref'] = get_pyobj_and_xincref

@specialize.ll()
def get_w_obj_and_decref(space, obj):
    """Decrement the reference counter of the PyObject and return the
    corresponding W_Root object (so the reference count is at least
    REFCNT_FROM_PYPY and cannot be zero).  Can be called with either
    a PyObject or a W_Root.
    """
    if is_pyobj(obj):
        pyobj = rffi.cast(PyObject, obj)
        w_obj = from_pyobj(space, pyobj)
    else:
        w_obj = obj
        pyobj = as_pyobj(space, w_obj)
    pyobj.c_ob_refcnt -= 1
    assert pyobj.c_ob_refcnt >= rawrefcount.REFCNT_FROM_PYPY
    keepalive_until_here(w_obj)
    return w_obj
INTERPLEVEL_API['get_w_obj_and_decref'] = get_w_obj_and_decref


@specialize.ll()
def new_pyobj(PYOBJ_TYPE, ob_type, length=None):
    if length is None:
        ob = lltype.malloc(PYOBJ_TYPE, flavor='raw', track_allocation=False)
    else:
        ob = lltype.malloc(PYOBJ_TYPE, length, flavor='raw',
                           track_allocation=False)
        ob.c_ob_size = length
    ob.c_ob_refcnt = 1
    ob.c_ob_type = ob_type
    ob.c_ob_pypy_link = 0
    return ob
INTERPLEVEL_API['new_pyobj'] = staticmethod(new_pyobj)


@specialize.ll()
def incref(space, obj):
    get_pyobj_and_incref(space, obj)
INTERPLEVEL_API['incref'] = incref

@specialize.ll()
def xincref(space, obj):
    get_pyobj_and_xincref(space, obj)
INTERPLEVEL_API['xincref'] = xincref

@specialize.ll()
def decref(space, obj):
    if is_pyobj(obj):
        obj = rffi.cast(PyObject, obj)
        assert obj.c_ob_refcnt > 0
        obj.c_ob_refcnt -= 1
        if obj.c_ob_refcnt == 0:
            _Py_Dealloc(space, obj)
    else:
        get_w_obj_and_decref(space, obj)
INTERPLEVEL_API['decref'] = decref

@specialize.ll()
def xdecref(space, obj):
    if obj:
        decref(space, obj)
INTERPLEVEL_API['xdecref'] = xdecref

# ----------

def make_ref(space, w_obj):
    ZZZ

def from_ref(space, ref):
    """
    Finds the interpreter object corresponding to the given reference.  If the
    object is not yet realized (see stringobject.py), creates it.
    """
    assert lltype.typeOf(ref) == PyObject
    ZZZ
    if not ref:
        return None
    state = space.fromcache(RefcountState)
    ptr = rffi.cast(ADDR, ref)

    try:
        return state.py_objects_r2w[ptr]
    except KeyError:
        pass

    # This reference is not yet a real interpreter object.
    # Realize it.
    ref_type = rffi.cast(PyObject, ref.c_ob_type)
    if ref_type == ref: # recursion!
        raise InvalidPointerException(str(ref))
    w_type = from_ref(space, ref_type)
    assert isinstance(w_type, W_TypeObject)
    return get_typedescr(w_type.instancetypedef).realize(space, ref)


@cpython_api([PyObject], lltype.Void)
def Py_IncRef(space, obj):
    xincref(space, obj)

@cpython_api([PyObject], lltype.Void)
def Py_DecRef(space, obj):
    xdecref(space, obj)


@cpython_api([PyObject], lltype.Void)
def _Py_NewReference(space, obj):
    ZZZ
    obj.c_ob_refcnt = 1
    w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
    assert isinstance(w_type, W_TypeObject)
    get_typedescr(w_type.instancetypedef).realize(space, obj)

@cpython_api([PyObject], lltype.Void)
def _Py_Dealloc(space, obj):
    from pypy.module.cpyext.api import generic_cpy_call
    pto = obj.c_ob_type
    #print >>sys.stderr, "Calling dealloc slot", pto.c_tp_dealloc, "of", obj, \
    #      "'s type which is", rffi.charp2str(pto.c_tp_name)
    generic_cpy_call(space, pto.c_tp_dealloc, obj)


#___________________________________________________________
# Support for borrowed references

def make_borrowed_ref(space, w_container, w_borrowed):
    """
    Create a borrowed reference, which will live as long as the container
    has a living reference (as a PyObject!)
    """
    ZZZ
    if w_borrowed is None:
        return lltype.nullptr(PyObject.TO)

    state = space.fromcache(RefcountState)
    return state.make_borrowed(w_container, w_borrowed)

class Reference:
    def __init__(self, pyobj):
        ZZZ
        assert not isinstance(pyobj, W_Root)
        self.pyobj = pyobj

    def get_ref(self, space):
        return self.pyobj

    def get_wrapped(self, space):
        return from_ref(space, self.pyobj)

class BorrowPair(Reference):
    """
    Delays the creation of a borrowed reference.
    """
    def __init__(self, w_container, w_borrowed):
        ZZZ
        self.w_container = w_container
        self.w_borrowed = w_borrowed

    def get_ref(self, space):
        return make_borrowed_ref(space, self.w_container, self.w_borrowed)

    def get_wrapped(self, space):
        return self.w_borrowed

def borrow_from(container, borrowed):
    return BorrowPair(container, borrowed)

#___________________________________________________________

@cpython_api([rffi.VOIDP], lltype.Signed, error=CANNOT_FAIL)
def _Py_HashPointer(space, ptr):
    return rffi.cast(lltype.Signed, ptr)
