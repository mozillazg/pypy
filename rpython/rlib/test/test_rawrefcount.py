from rpython.rlib import rawrefcount
from rpython.rtyper.lltypesystem import lltype, llmemory

class W_Root(object):
    def __init__(self, intval=0):
        self.intval = intval

PyObjectS = lltype.Struct('PyObjectS',
                          ('ob_refcnt', lltype.Signed),
                          ('ob_pypy_link', llmemory.GCREF))
PyObject = lltype.Ptr(PyObjectS)


def test_create_link_from_pypy():
    p = W_Root(42)
    ob = lltype.malloc(PyObjectS, flavor='raw', zero=True,
                       track_allocation=False)
    assert rawrefcount.from_obj(PyObjectS, p) == lltype.nullptr(PyObjectS)
    assert rawrefcount.to_obj(W_Root, ob) == None
    rawrefcount.create_link_from_pypy(p, ob)
    assert rawrefcount.from_obj(PyObjectS, p) == ob
    assert rawrefcount.to_obj(W_Root, ob) == p

def test_create_link_to_pypy():
    p = W_Root(42)
    ob = lltype.malloc(PyObjectS, flavor='raw', zero=True,
                       track_allocation=False)
    assert rawrefcount.from_obj(PyObjectS, p) == lltype.nullptr(PyObjectS)
    assert rawrefcount.to_obj(W_Root, ob) == None
    rawrefcount.create_link_to_pypy(p, ob)
    assert rawrefcount.from_obj(PyObjectS, p) == lltype.nullptr(PyObjectS)
    assert rawrefcount.to_obj(W_Root, ob) == p
