
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

def test_stringstar():
    import py
    py.test.skip("completely broken")
    c_source = """
    int f(char *args[]) {
        char **p = args;
        int l = 0;
        while (p) {
            l += strlen(p*);
            p++;
        }
        return (l);
    }
    """
    elem_T = lltype.FixedSizeArray(lltype.Char, 1)
    T = lltype.FixedSizeArray(Ptr(elem_T), 1) # this is char**
    z = llexternal('f', [Ptr(T)], Signed, includes=['stdio.h'])
    alloc_T = lltype.Array(CCHARP)

    def f():
        ss = malloc(alloc_T, 4, flavor='raw')
        ref1, ss[0] = str2charp("xxx")
        ref2, ss[1] = str2charp("x")
        ref3, ss[2] = str2charp("xxxx")
        _, ss[3] = lltype.nullptr(elem_T)
        to_fun = lltype._subarray._makeptr(ss._obj, 0, ss._solid)
        return z(to_fun)

    xf = compile(f, [])
    assert xf() == 8
