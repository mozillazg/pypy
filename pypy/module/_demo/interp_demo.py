
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.objspace.std.stdtypedef import SMM, StdTypeDef
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.model import W_Object
from pypy.interpreter.gateway import interp2app

def w_type(space, w_subtype, arg):
    # XXX handle subclasses
    if arg == 0:
        return W_Zero()
    else:
        return W_One()
w_type.unwrap_spec = [ObjSpace, W_Root, int]

tp_pop    = SMM('pop',    2, defaults=(-1,))

type_typedef = StdTypeDef("tp", __new__ = interp2app(w_type))
type_typedef.registermethods(globals())

class W_Zero(W_Object):
    @staticmethod
    def register(typeorder):
        typeorder[W_Zero] = []
        
    typedef = type_typedef

class W_One(W_Object):
    @staticmethod
    def register(typeorder):
        typeorder[W_One] = []
        
    typedef = type_typedef

def repr__Zero(space, w_zero):
    return space.wrap("zero")

def repr__One(space, w_one):
    return space.wrap("one")


def len__Zero(space, w_zero):
    return space.wrap(7)

def len__One(space, w_zero):
    return space.wrap(42)


def tp_pop__One_ANY(space, w_one, w_count):
    return w_count

def tp_pop__Zero_ANY(space, w_zero, w_count):
    return space.wrap(9)


register_all(locals(), globals())
