
#import py
from pypy.rpython.lltypesystem.rffi import llexternal, str2charp, CCHARP
from pypy.translator.c.test.test_genc import compile
from pypy.rpython.lltypesystem.lltype import Signed, Ptr, Char, malloc
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir

def test_basic():
    c_source = """
    int z(int x)
    {
        return (x + 3);
    }
    """
    c_file = udir.join("stuff.c")
    c_file.write(c_source)
    z = llexternal('z', [Signed], Signed, sources=[str(c_file)])

    def f():
        return z(8)

    xf = compile(f, [])
    assert xf() == 8+3

def test_hashdefine():
    c_source = """
    #define X(i) (i+3)
    """

    c_file = udir.join("stuff.c")
    c_file.write(c_source)

    z = llexternal('X', [Signed], Signed, includes=[str(c_file)])

    def f():
        return z(8)

    xf = compile(f, [])
    assert xf() == 8+3

def test_string():
    z = llexternal('strlen', [Ptr(CCHARP)], Signed, includes=['stdio.h'])

    def f():
        s = str2charp("xxx")
        res = z(s)
        lltype.free(s, flavor='raw')
        return res

    xf = compile(f, [], backendopt=False)
    assert xf() == 3
