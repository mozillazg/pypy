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


def _reset_state():
    global _p_list, _o_list, _s_list, _adr2pypy, _pypy2ob
    _p_list = []     # not rpython
    _o_list = []     # not rpython
    _s_list = []     # not rpython
    _adr2pypy = [None]  # not rpython
    _pypy2ob = {}       # not rpython
_reset_state()

def _build_pypy_link(p):
    res = len(_adr2pypy)
    _adr2pypy.append(p)
    return res


def create_link_pypy(p, ob):
    "NOT_RPYTHON: a link where the PyPy object contains all the data"
    assert p not in _pypy2ob
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = _build_pypy_link(p)
    ob.c_ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    _pypy2ob[p] = ob
    _p_list.append(ob)

def create_link_pyobj(p, ob):
    """NOT_RPYTHON: a link where the PyObject contains all the data.
       from_obj() will not work on this 'p'."""
    assert p not in _pypy2ob
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = _build_pypy_link(p)
    ob.c_ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    _o_list.append(ob)

def create_link_shared(p, ob):
    """NOT_RPYTHON: a link where both p and ob contain some data.
       from_obj() will not work on this 'p'."""
    assert p not in _pypy2ob
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = _build_pypy_link(p)
    ob.c_ob_refcnt += REFCNT_FROM_PYPY_OBJECT
    _s_list.append(ob)

def from_obj(OB_PTR_TYPE, p):
    "NOT_RPYTHON"
    ob = _pypy2ob.get(p)
    if ob is None:
        return lltype.nullptr(OB_PTR_TYPE.TO)
    assert lltype.typeOf(ob) == OB_PTR_TYPE
    return ob

@specialize.arg(0)
def to_obj(Class, ob):
    link = ob.c_ob_pypy_link
    if we_are_translated():
        pypy_gcref = lltype.cast_int_to_ptr(llmemory.GCREF, link)
        return annlowlevel.cast_gcref_to_instance(Class, pypy_gcref)
    else:
        if link == 0:
            return None
        p = _adr2pypy[link]
        assert isinstance(p, Class)
        return p

def _collect():
    """NOT_RPYTHON: for tests only.  Emulates a GC collection.
    Returns the list of ob's whose _Py_Dealloc() should be called,
    from the O list.
    """
    def detach(ob, wr_list):
        assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY_OBJECT
        assert ob.c_ob_pypy_link
        p = _adr2pypy[ob.c_ob_pypy_link]
        assert p is not None
        _adr2pypy[ob.c_ob_pypy_link] = None
        wr_list.append((ob, weakref.ref(p)))
        return p

    global _p_list, _o_list, _s_list
    wr_p_list = []
    new_p_list = []
    for ob in _p_list:
        if ob.c_ob_refcnt > REFCNT_FROM_PYPY_OBJECT:
            new_p_list.append(ob)
        else:
            p = detach(ob, wr_p_list)
            del _pypy2ob[p]
            del p
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
            assert ob.c_ob_pypy_link
            _adr2pypy[ob.c_ob_pypy_link] = p
            final_list.append(ob)
            return p
        else:
            ob.c_ob_refcnt -= REFCNT_FROM_PYPY_OBJECT
            ob.c_ob_pypy_link = 0
            if ob.c_ob_refcnt == 0 and dealloc is not None:
                dealloc.append(ob)
            return None

    _p_list = new_p_list
    dealloc = None
    for ob, wr in wr_p_list:
        p = attach(ob, wr, _p_list)
        if p:
            _pypy2ob[p] = ob
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
