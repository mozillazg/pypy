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
    "NOT_RPYTHON: for tests only"
    global _p_list
    wrlist = []
    newlist = []
    for ob in _p_list:
        assert ob.ob_refcnt >= REFCNT_FROM_PYPY_OBJECT
        if ob.ob_refcnt == REFCNT_FROM_PYPY_OBJECT:
            wrlist.append(weakref.ref(ob))
        else:
            newlist.append(ob)
    _p_list = newlist
    del ob
    rgc.collect()  # forces the cycles to be resolved and the weakrefs to die
    for wr in wrlist:
        ob = wr()
        if ob is not None:
            newlist.append(ob)

# ____________________________________________________________

## class Entry(ExtRegistryEntry):
##     _about_ = create_link_from_pypy
