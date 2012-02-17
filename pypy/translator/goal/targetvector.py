
from pypy.rpython.lltypesystem import lltype
from pypy.rlib import jit

TP = lltype.Array(lltype.Float, hints={'nolength': True,
                                       'memory_position_alignment': 16})

driver = jit.JitDriver(greens = [], reds = ['a', 'i', 'b', 'size'])

def initialize(arr, size):
    for i in range(size):
        arr[i] = float(i)

def sum(arr, size):
    s = 0
    for i in range(size):
        s += arr[i]
    return s

def main(n, size):
    a = lltype.malloc(TP, size, flavor='raw', zero=True)
    b = lltype.malloc(TP, size, flavor='raw', zero=True)
    initialize(a, size)
    initialize(b, size)
    for i in range(n):
        f(a, b, size)
    lltype.free(a, flavor='raw')
    lltype.free(b, flavor='raw')

def f(a, b, size):
    i = 0
    while i < size:
        driver.jit_merge_point(a=a, i=i, size=size, b=b)
        jit.assert_aligned(a, i)
        jit.assert_aligned(b, i)
        b[i] = a[i] + a[i]
        i += 1
        b[i] = a[i] + a[i]
        i += 1

def entry_point(argv):
    main(int(argv[1]), int(argv[2]))
    return 0

def jitpolicy(driver):
    return None

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
