
from pypy.jit.backend.x86.support import ListOfFloats
from pypy.rpython.lltypesystem import rffi, lltype

def test_append():
    x = ListOfFloats(2)
    assert x.length() == 0
    assert len(x.chunks) == 0
    x.append(3.0)
    x.append(2.0)
    assert x.length() == 2
    assert len(x.chunks) == 1
    x.append(1.0)
    assert x.length() == 3
    assert len(x.chunks) == 2
    assert x.chunks[0].ll_array[0] == 3.0
    assert x.chunks[0].ll_array[1] == 2.0
    assert x.chunks[1].ll_array[0] == 1.0

def test_getitem():
    x = ListOfFloats(2)
    assert x.append(3.0) == 0
    assert x.append(2.0) == 1
    assert x.append(1.0) == 2
    assert x.getitem(0) == 3.0
    assert x.getitem(1) == 2.0
    assert x.getitem(2) == 1.0

def test_get():
    x = ListOfFloats(2)
    assert x.get(0.0) == 0
    assert x.get(0.0) == 0
    assert x.get(0.5) == 1
    assert x.get(0.0) == 0
    assert x.get(2.0) == 2

def test_getaddr():
    x = ListOfFloats(2)
    base = x.getaddr(0.0)
    assert x.getaddr(0.0) == base
    assert x.getaddr(1.0) - base == rffi.sizeof(lltype.Float)

    
    
