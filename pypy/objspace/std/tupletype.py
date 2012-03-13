import sys
from pypy.interpreter import gateway
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM


MAXIMUM_SPECIALIZED_SIZE = 8

def wraptuple(space, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject

    w_tuple = space.allocate_instance(W_TupleObject, space.w_tuple)
    make_tuple(space, w_tuple, list_w)
    return w_tuple

def make_tuple(space, w_tuple, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject, get_shape_cache

    cache = get_shape_cache(space)
    if len(list_w) > MAXIMUM_SPECIALIZED_SIZE:
        W_TupleObject.__init__(w_tuple, cache.large_shape, list_w)
    else:
        types = []
        items = []
        for w_item in list_w:
            types.append(cache.object_shapetype)
            items.append(w_item)

        shape = cache.find_shape(types)
        W_TupleObject.__init__(w_tuple, shape, items)
        return W_TupleObject(shape, items)

tuple_count = SMM("count", 2,
                  doc="count(obj) -> number of times obj appears in the tuple")

tuple_index = SMM("index", 4, defaults=(0, sys.maxint),
                  doc="index(obj, [start, [stop]]) -> first index that obj "
                  "appears in the tuple")


def descr__new__(space, w_tupletype, w_sequence=gateway.NoneNotWrapped):
    from pypy.objspace.std.tupleobject import W_TupleObject

    if w_sequence is None:
        tuple_w = []
    elif (space.is_w(w_tupletype, space.w_tuple) and
          space.is_w(space.type(w_sequence), space.w_tuple)):
        return w_sequence
    else:
        tuple_w = space.fixedview(w_sequence)
    w_obj = space.allocate_instance(W_TupleObject, w_tupletype)
    make_tuple(space, w_obj, tuple_w)
    return w_obj

# ____________________________________________________________

tuple_typedef = StdTypeDef("tuple",
    __doc__ = '''tuple() -> an empty tuple
tuple(sequence) -> tuple initialized from sequence's items

If the argument is a tuple, the return value is the same object.''',
    __new__ = gateway.interp2app(descr__new__),
    )
tuple_typedef.registermethods(globals())
