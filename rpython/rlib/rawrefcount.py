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


def create_link_from_pypy(p, ob):
    "NOT_RPYTHON"
    assert not hasattr(p, '__rawrefcount')
    assert not ob.ob_pypy_link
    ob.ob_pypy_link = rgc.cast_instance_to_gcref(p)
    ob.ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    p.__rawrefcount = ob
    _p_list.append(ob)

def create_link_to_pypy(p, ob):
    "NOT_RPYTHON"
    assert not ob.ob_pypy_link
    ob.ob_pypy_link = rgc.cast_instance_to_gcref(p)
    ob.ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    _o_list.append(ob)

def from_obj(OBTYPE, p):
    "NOT_RPYTHON"
    null = lltype.nullptr(OBTYPE)
    ob = getattr(p, '__rawrefcount', null)
    assert lltype.typeOf(ob) == lltype.Ptr(OBTYPE)
    return ob

@specialize.arg(0)
def to_obj(Class, ob):
    pypy_gcref = ob.ob_pypy_link
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
    global _p_list, _o_list
    wr_p_list = []
    new_p_list = []
    for ob in _p_list:
        assert ob.ob_refcnt >= REFCNT_FROM_PYPY_OBJECT
        if ob.ob_refcnt == REFCNT_FROM_PYPY_OBJECT:
            wr_p_list.append(weakref.ref(ob))
        else:
            new_p_list.append(ob)
        ob = None
    _p_list = Ellipsis
    #
    wr_o_list = []
    for ob in _o_list:
        assert ob.ob_pypy_link
        p = rgc.try_cast_gcref_to_instance(object, ob.ob_pypy_link)
        assert p is not None
        ob.ob_pypy_link = lltype.nullptr(llmemory.GCREF.TO)
        wr_o_list.append((ob, weakref.ref(p)))
        p = None
    _o_list = Ellipsis
    #
    rgc.collect()  # forces the cycles to be resolved and the weakrefs to die
    rgc.collect()
    rgc.collect()
    #
    _p_list = new_p_list
    for wr in wr_p_list:
        ob = wr()
        if ob is not None:
            _p_list.append(ob)
    #
    dealloc = []
    _o_list = []
    for ob, wr in wr_o_list:
        p = wr()
        if p is not None:
            ob.ob_pypy_link = rgc.cast_instance_to_gcref(p)
            _o_list.append(ob)
        else:
            assert ob.ob_refcnt >= REFCNT_FROM_PYPY_OBJECT
            ob.ob_refcnt -= REFCNT_FROM_PYPY_OBJECT
            if ob.ob_refcnt == 0:
                dealloc.append(ob)
    return dealloc

# ____________________________________________________________

## class Entry(ExtRegistryEntry):
##     _about_ = create_link_from_pypy
