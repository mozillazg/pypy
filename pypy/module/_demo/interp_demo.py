
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.objspace.std.stdtypedef import SMM, StdTypeDef
from pypy.objspace.std.register_all import register_all

def w_type(space, arg):
    if arg == 0:
        return space.wrap(W_Zero())
    else:
        return space.wrap(W_One())
w_type.unwrap_spec = [ObjSpace, int]

type_repr = SMM('__repr__', 1, 'a docstring')

type_typedef = StdTypeDef("tp",
                          __new__ = w_type)
type_typedef.registermethods(globals())

class W_Zero(Wrappable):
    typedef = type_typedef

class W_One(Wrappable):
    typedef = type_typedef

def repr__Zero(space, w_zero):
    return space.wrap("zero")

def repr__One(space, w_one):
    return space.wrap("one")

register_all(locals(), globals())
