class AbstractArg(object):
    next = None

class IntArg(AbstractArg):

    def __init__(self, intval):
        self.intval = intval

    def push(self, funcptr):
        funcptr.push_arg(self.intval)

class FloatArg(AbstractArg):

    def __init__(self, floatval):
        self.floatval = floatval

    def push(self, funcptr):
        funcptr.push_arg(self.floatval)


class Func(object):

    def __init__(self, funcptr):
        # XXX: for now, this is just a wrapper around libffi.FuncPtr, but in
        # the future it will replace it completely
        self.funcptr = funcptr

    def call(self, argchain, RESULT):
        # implementation detail
        arg = argchain
        while arg:
            arg.push(self.funcptr)
            arg = arg.next
        return self.funcptr.call(RESULT)
    call._annspecialcase_ = 'specialize:arg(1)'


