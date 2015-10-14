#
#  See documentation in pypy/doc/discussion/rawrefcount.rst
#
import weakref
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper import annlowlevel
from rpython.rlib import rgc


REFCNT_FROM_PYPY_OBJECT = 80   # == 0x50


_p_list = []     # not rpython
_o_list = []     # not rpython
_s_list = []     # not rpython


def create_link_pypy(p, ob):
    "NOT_RPYTHON: a link where the PyPy object contains all the data"
    assert not hasattr(p, '__rawrefcount')
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = rgc.cast_instance_to_gcref(p)
    ob.c_ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    p.__rawrefcount = ob
    _p_list.append(ob)

def create_link_pyobj(p, ob):
    """NOT_RPYTHON: a link where the PyObject contains all the data.
       from_obj() will not work on this 'p'."""
    assert not hasattr(p, '__rawrefcount')
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = rgc.cast_instance_to_gcref(p)
    ob.c_ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    p.__rawrefcount = lltype.nullptr(lltype.typeOf(ob).TO)
    _o_list.append(ob)

def create_link_shared(p, ob):
    """NOT_RPYTHON: a link where both p and ob contain some data.
       from_obj() will not work on this 'p'."""
    assert not hasattr(p, '__rawrefcount')
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = rgc.cast_instance_to_gcref(p)
    ob.c_ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    p.__rawrefcount = lltype.nullptr(lltype.typeOf(ob).TO)
    _s_list.append(ob)

def from_obj(OBTYPE, p):
    "NOT_RPYTHON"
    null = lltype.nullptr(OBTYPE)
    ob = getattr(p, '__rawrefcount', null)
    assert lltype.typeOf(ob) == lltype.Ptr(OBTYPE)
    return ob

@specialize.arg(0)
def to_obj(Class, ob):
    pypy_gcref = ob.c_ob_pypy_link
    if we_are_translated():
        return annlowlevel.cast_gcref_to_instance(Class, pypy_gcref)
    else:
        if not pypy_gcref:
            return None
        p = rgc.try_cast_gcref_to_instance(Class, pypy_gcref)
        assert p is not None
        return p

def _collect():
    """NOT_RPYTHON: for tests only.  Emulates a GC collection.
    Returns the list of ob's whose _Py_Dealloc() should be called,
    from the O list.
    """
    def detach(ob, wr_list):
        assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY_OBJECT
        assert ob.c_ob_pypy_link
        p = rgc.try_cast_gcref_to_instance(object, ob.c_ob_pypy_link)
        assert p is not None
        ob.c_ob_pypy_link = lltype.nullptr(llmemory.GCREF.TO)
        wr_list.append((ob, weakref.ref(p)))

    global _p_list, _o_list, _s_list
    wr_p_list = []
    new_p_list = []
    for ob in _p_list:
        if ob.c_ob_refcnt > REFCNT_FROM_PYPY_OBJECT:
            new_p_list.append(ob)
        else:
            wr_p_list.append(weakref.ref(ob))
        ob = None
    _p_list = Ellipsis

    wr_s_list = []
    new_s_list = []
    for ob in _s_list:
        if ob.c_ob_refcnt > REFCNT_FROM_PYPY_OBJECT:
            new_s_list.append(ob)
        else:
            detach(ob, wr_s_list)
        ob = None
    _s_list = Ellipsis

    wr_o_list = []
    for ob in _o_list:
        detach(ob, wr_o_list)
    _o_list = Ellipsis

    rgc.collect()  # forces the cycles to be resolved and the weakrefs to die
    rgc.collect()
    rgc.collect()

    def attach(ob, wr, final_list):
        assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY_OBJECT
        p = wr()
        if p is not None:
            ob.c_ob_pypy_link = rgc.cast_instance_to_gcref(p)
            final_list.append(ob)
        else:
            ob.c_ob_refcnt -= REFCNT_FROM_PYPY_OBJECT
            if ob.c_ob_refcnt == 0:
                dealloc.append(ob)

    _p_list = new_p_list
    for wr in wr_p_list:
        ob = wr()
        if ob is not None:
            _p_list.append(ob)
    #
    dealloc = []
    _s_list = new_s_list
    for ob, wr in wr_s_list:
        attach(ob, wr, _s_list)
    _o_list = []
    for ob, wr in wr_o_list:
        attach(ob, wr, _o_list)
    return dealloc

# ____________________________________________________________

## class Entry(ExtRegistryEntry):
##     _about_ = create_link_from_pypy
