
def f():
    print 543210

    i = 0
    while i < 100:
        # XXX implement inplace_add method for ints
        if i % 2:
            i = i + 3
        else:
            i = i + 1
    print i        # should print 102

f()
