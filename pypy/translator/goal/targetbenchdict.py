"""
A simple standalone target.

The target below specifies None as the argument types list.
This is a case treated specially in driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""


# __________  Entry point  __________

class A(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

def entry_point(argv):
    bench_no = int(argv[1])
    bench_counter = int(argv[2])
    repeats = int(argv[3])
    for k in range(repeats):
        if bench_no == 1:
            d = {}
            for i in range(bench_counter):
                d[str(i)] = None
        if bench_no == 2: 
            d = {}
            for i in range(bench_counter):
                d[i] = A(1, 2, 3)
        if bench_no == 3:
            d = {}
            a = A(1, 2, 3)
            for i in range(bench_counter):
                if i % 100 == 0:
                    a = A(1, 2, 3)
                d[i] = a
        if bench_no == 4:
            d = {}
            s = 0
            for i in range(bench_counter):
                d[i % 100] = i
                s += d[i % 100]
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
