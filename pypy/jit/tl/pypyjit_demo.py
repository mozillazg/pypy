## base = object

## class Number(base):
##     __slots__ = ('val', )
##     def __init__(self, val=0):
##         self.val = val

##     def __add__(self, other):
##         if not isinstance(other, int):
##             other = other.val
##         return Number(val=self.val + other)
            
##     def __cmp__(self, other):
##         val = self.val
##         if not isinstance(other, int):
##             other = other.val
##         return cmp(val, other)

##     def __nonzero__(self):
##         return bool(self.val)

## def g(x, inc=2):
##     return x + inc

## def f(n, x, inc):
##     while x < n:
##         x = g(x, inc=1)
##     return x

## import time
## #t1 = time.time()
## #f(10000000, Number(), 1)
## #t2 = time.time()
## #print t2 - t1
## t1 = time.time()
## f(10000000, 0, 1)
## t2 = time.time()
## print t2 - t1

def main():
    from _ffi import CDLL, types
    libm = CDLL('libm.so')
    pow = libm.getfunc('pow', [types.double, types.double], types.double)
    i = 0
    while i < 100:
        res = pow(2, 3)
        i += 1
    print res

try:
    main()
except Exception, e:
    print "Exception: ", type(e)
    print e
    
## def f():
##     a=7
##     i=0
##     while i<4:
##         if  i<0: break
##         if  i<0: break
##         i+=1

## f()
