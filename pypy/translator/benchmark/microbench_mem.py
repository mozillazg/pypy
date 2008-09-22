#!/usr/bin/env python
import autopath
""" This file attempts to measure how much memory is taken by various objects.
"""

from pypy.translator.benchmark.bench_mem import measure, smaps_measure_func
import py

def measure_func(num, pid):
    res = smaps_measure_func(pid)
    print 2**num, res.private

def tuples(read, write, coeff):
    import gc
    x = ()
    for i in range(1000 * coeff):
        x = (x,)
    gc.collect()
    write('x')
    read()
    write('e')

def linked_list(read, write, coeff):
    import gc

    class A(object):
        def __init__(self, other):
            self.other = other

    x = None
    for i in range(1000 * coeff):
        x = A(x)
    gc.collect()
    write('x')
    read()
    write('e')

def list_of_instances_with_int(read, write, coeff):
    import gc

    class A(object):
        def __init__(self, x):
            self.x = x

    x = [A(i) for i in range(1000 * coeff)]
    gc.collect()
    write('x')
    read()
    write('e')

def linked_list_with_floats(read, write, coeff):
    import gc

    class A(object):
        def __init__(self, other, i):
            self.i = float(i)
            self.other = other

    x = None
    for i in range(1000 * coeff):
        x = A(x, i)
        if i % 1000 == 0:
            gc.collect()
    gc.collect()
    write('x')
    read()
    write('e')

def empty_instances(read, write, coeff):
    import gc
    class A(object):
        pass

    x = [A() for i in range(1000*coeff)]
    gc.collect()
    write('x')
    read()
    write('e')

def lists(read, write, coeff):
    import gc
    x = []
    for i in range(1000 * coeff):
        x = [x]
    gc.collect()
    write('x')
    read()
    write('e')

if __name__ == '__main__':
    coeff = 1
    i = 0
    funcs = []
    while i < 9:
        funcs.append(lambda r, w, coeff=coeff:
                     linked_list_with_floats(r, w, coeff))
        coeff *= 2
        i += 1
    res = measure(measure_func, funcs)
