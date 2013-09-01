import cffi, py, sys, random
from rpython.tool.udir import udir
from rpython.rlib.rarithmetic import LONG_BIT


testdir = udir.join('test_c_support').ensure(dir=True)
testdir.join('common_header.h').write("""
typedef long Signed;
#define PYPY_LONG_BIT %d
#define RPY_LL_ASSERT
""" % LONG_BIT)

srcdir = py.path.local(__file__).join('..', '..', 'src')


ffi = cffi.FFI()
ffi.cdef("""
typedef long Signed;
void RPyRawMalloc_Record_Size(void *, Signed);
void RPyRawMalloc_Forget_Size(void *);
Signed RPyRawMalloc_Size(void *);
""")

lib = ffi.verify(srcdir.join('debug_rawmem.c').read(),
                 include_dirs=[str(testdir), str(srcdir.join('..'))])


def test_simple():
    p = ffi.cast("void *", 1234567)
    lib.RPyRawMalloc_Record_Size(p, 321)
    s = lib.RPyRawMalloc_Size(p)
    assert s == 321
    s = lib.RPyRawMalloc_Size(ffi.cast("void *", 189729))
    assert s == sys.maxint
    lib.RPyRawMalloc_Forget_Size(p)
    s = lib.RPyRawMalloc_Size(p)
    assert s == sys.maxint

def test_random():
    expected = {}
    for i in range(10000):
        what = random.randrange(0, 4)
        if what == 0:
            ptr = ffi.cast("void *", random.randrange(1, sys.maxint))
            size = random.randrange(1, sys.maxint)
            lib.RPyRawMalloc_Record_Size(ptr, size)
            expected[ptr] = size
        elif what == 1:
            if not expected:
                continue
            ptr = random.choice(list(expected))
            expected_size = expected[ptr]
            actual_size = lib.RPyRawMalloc_Size(ptr)
            assert actual_size == expected_size
        elif what == 2:
            ptr = ffi.cast("void *", random.randrange(1, sys.maxint))
            actual_size = lib.RPyRawMalloc_Size(ptr)
            assert actual_size == expected.get(ptr, sys.maxint)
        else:
            if not expected:
                continue
            ptr = random.choice(list(expected))
            if expected[ptr] != sys.maxint:
                lib.RPyRawMalloc_Forget_Size(ptr)
                expected[ptr] = sys.maxint
