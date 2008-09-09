#!/usr/bin/env python
import autopath
""" This file attempts to measure how much memory is taken by various objects.
"""

from pypy.translator.benchmark.bench_mem import measure, smaps_measure_func
import py

def measure_func(num, pid):
    res = smaps_measure_func(pid)
    print num, res.private

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

if __name__ == '__main__':
    coeff = 1
    i = 0
    funcs = []
    while i < 10:
        f = py.code.Source(list_of_instances_with_int, """
        def f(r, w):
            list_of_instances_with_int(r, w, %d)
        """ % coeff)
        funcs.append((f, 'f'))
        coeff *= 2
        i += 1
    res = measure(measure_func, funcs)
