
from pypy.rlib.clibffi import *
from pypy.rlib.objectmodel import specialize

class AbstractArg(object):
    next = None

class IntArg(AbstractArg):
    """ An argument holding an integer
    """

    def __init__(self, intval):
        self.intval = intval

    def push(self, funcptr):
        funcptr.push_arg(self.intval)

class FloatArg(AbstractArg):
    """ An argument holding a float
    """

    def __init__(self, floatval):
        self.floatval = floatval

    def push(self, funcptr):
        funcptr.push_arg(self.floatval)

class Func(object):

    def __init__(self, funcptr):
        # XXX: for now, this is just a wrapper around libffi.FuncPtr, but in
        # the future it will replace it completely
        self.funcptr = funcptr

    @specialize.arg(2)
    def call(self, argchain, RESULT):
        # implementation detail
        arg = argchain
        while arg:
            arg.push(self.funcptr)
            arg = arg.next
        return self.funcptr.call(RESULT)


