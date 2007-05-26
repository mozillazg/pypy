
#import py
from pypy.rpython.lltypesystem.rffi import *
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
    z = llexternal('strlen', [CCHARP], Signed, includes=['string.h'])

    def f():
        s = str2charp("xxx")
        res = z(s)
        lltype.free(s, flavor='raw')
        return res

    xf = compile(f, [], backendopt=False)
    assert xf() == 3

def test_stringstar():
    c_source = """
    #include <string.h>
    
    int f(char *args[]) {
        char **p = args;
        int l = 0;
        while (*p) {
            l += strlen(*p);
            p++;
        }
        return (l);
    }
    """
    c_file = udir.join("stringstar.c")
    c_file.write(c_source)
    z = llexternal('f', [CCHARPP], Signed, sources=[str(c_file)])

    def f():
        l = ["xxx", "x", "xxxx"]
        ss = liststr2charpp(l)
        result = z(ss)
        free_charpp(ss)
        return result

    xf = compile(f, [], backendopt=False)
    assert xf() == 8

def test_struct():
    h_source = """
    struct xx {
       int one;
       char two;
       int three;
    };
    """
    h_file = udir.join("structxx.h")
    h_file.write(h_source)
    
    c_source = """
    #include "structxx.h"
    int f(struct xx* z)
    {
      return (z->one + z->three);
    }
    """
    TP = CStruct('xx', ('one', Signed), ('two', Char), ('three', Signed))

    c_file = udir.join("structxx.c")
    c_file.write(c_source)
    z = llexternal('f', [TP], Signed, sources=[str(c_file)],
                   includes=[str(h_file)])

    def f():
        struct = lltype.malloc(TP.TO, flavor='raw')
        struct.c_one = 3
        struct.c_two = '\x33'
        struct.c_three = 5
        result = z(struct)
        lltype.free(struct, flavor='raw')
        return result

    fn = compile(f, [], backendopt=False)
    assert fn() == 8

