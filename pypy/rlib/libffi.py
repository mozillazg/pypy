from pypy.rlib.clibffi import *
from pypy.rlib.objectmodel import specialize
from pypy.rlib import jit


class AbstractArg(object):
    next = None

class IntArg(AbstractArg):
    """ An argument holding an integer
    """

    def __init__(self, intval):
        self.intval = intval

    def push(self, func):
        func._push_arg(self.intval)

class FloatArg(AbstractArg):
    """ An argument holding a float
    """

    def __init__(self, floatval):
        self.floatval = floatval

    def push(self, func):
        func._push_arg(self.floatval)

class Func(object):

    _immutable_fields_ = ['funcptr', 'funcsym', 'argtypes', 'restype']

    def __init__(self, funcptr):
        # XXX: for now, this is just a wrapper around clibffi.FuncPtr, but in
        # the future it will replace it completely
        self.funcptr = funcptr
        self.funcsym = funcptr.funcsym
        self.argtypes = funcptr.argtypes
        self.restype = funcptr.restype

    def _prepare(self):
        pass
    _prepare.oopspec = 'libffi_prepare_call(self)'

    def _push_arg(self, value):
        self.funcptr.push_arg(value)
    # XXX this is bad, fix it somehow in the future, but specialize:argtype
    # doesn't work correctly with mixing non-negative and normal integers
    _push_arg._annenforceargs_ = [None, int]
    #push_arg._annspecialcase_ = 'specialize:argtype(1)'
    _push_arg.oopspec = 'libffi_push_arg(self, value)'

    def _do_call(self, funcsym, RESULT):
        return self.funcptr.call(RESULT)
    _do_call._annspecialcase_ = 'specialize:arg(2)'
    _do_call.oopspec = 'libffi_call(self, funcsym, RESULT)'

    @jit.unroll_safe
    @specialize.arg(2)
    def call(self, argchain, RESULT):
        self._prepare()
        arg = argchain
        while arg:
            arg.push(self)
            arg = arg.next
        #return self.funcptr.call(RESULT)
        return self._do_call(self.funcsym, RESULT)
