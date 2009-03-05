
def f0():
    print "simple loop"

    i = 0
    while i < 100:
        i = i + 3
    print i

def f1():
    print "simple loop with inplace_add"

    i = 0
    while i < 100:
        i += 3
    print i

def f():
    print 543210

    s = 0
    for i in range(100):
        # XXX implement inplace_add method for ints
        s = s + i
    print s        # should print 102

f()
