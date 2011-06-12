from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

from pypy.rlib.rtealet import _make_classes, TealetError

# ____________________________________________________________

W_Tealet, W_MainTealet = _make_classes(Wrappable)
W_Tealet.__name__     = 'W_Tealet'
W_MainTealet.__name__ = 'W_MainTealet'

class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("tealet.error")

def wrap_error(space, error):
    w_exception_class = space.fromcache(Cache).w_error
    w_exception = space.call_function(w_exception_class, space.wrap(error.msg))
    return OperationError(w_exception_class, w_exception)

# ____________________________________________________________

def W_Tealet_run(self):
    space = self.space
    w_other = space.call_method(space.wrap(self), 'run')
    return space.interp_w(W_Tealet, w_other, can_be_None=True)

def W_Tealet___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_Tealet, w_subtype)
    r.space = space
    return space.wrap(r)

def W_Tealet_switch(w_self):
    self = space.interp_w(W_Tealet, w_self)
    try:
        self.switch()
    except TealetError, e:
        raise wrap_error(space, e)

W_Tealet.run = W_Tealet_run
W_Tealet.typedef = TypeDef(
        'Tealet',
        __module__ = 'tealet',
        __new__ = interp2app(W_Tealet___new__),
        switch = interp2app(W_Tealet_switch),
        )

# ____________________________________________________________

def W_MainTealet___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_MainTealet, w_subtype)
    r.__init__()
    r.space = space
    return space.wrap(r)

def W_MainTealet_start(w_self, w_tealet):
    space = self.space
    self = space.interp_w(W_MainTealet, w_self)
    tealet = space.interp_w(W_Tealet, w_tealet)
    try:
        self.start(tealet)
    except TealetError, e:
        raise wrap_error(space, e)

W_MainTealet.typedef = TypeDef(
        'MainTealet',
        __module__ = 'tealet',
        __new__ = interp2app(W_MainTealet___new__),
        start = interp2app(W_MainTealet_start),
        )

# ____________________________________________________________
