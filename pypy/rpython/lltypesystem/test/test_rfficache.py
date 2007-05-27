
from pypy.rpython.lltypesystem.rfficache import sizeof_c_type

def test_sizeof_c_type():
    sizeofchar = sizeof_c_type('char')
    assert sizeofchar == 8
