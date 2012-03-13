import sys
from pypy.rlib.rerased_raw import UntypedStorage, INT, INSTANCE
from pypy.interpreter import gateway
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM


MAXIMUM_SPECIALIZED_SIZE = 8

def wraptuple(space, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject

    w_tuple = space.allocate_instance(W_TupleObject, space.w_tuple)
    make_tuple(space, w_tuple, list_w)
    return w_tuple

def get_char_from_obj(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_int):
        return INT
    else:
        return INSTANCE

def store_obj(space, storage, idx, w_obj):
    if space.is_w(space.type(w_obj), space.w_int):
        storage.setint(idx, space.int_w(w_obj))
    else:
        storage.setinstance(idx, w_obj)

def make_tuple(space, w_tuple, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject

    shape_chars = ["\x00"] * len(list_w)
    for i, w_item in enumerate(list_w):
        shape_chars[i] = get_char_from_obj(space, w_item)

    shape = space.str_w(space.new_interned_str("".join(shape_chars)))
    storage = UntypedStorage(shape)
    for i, w_item in enumerate(list_w):
        store_obj(space, storage, i, w_item)
    W_TupleObject.__init__(w_tuple, storage)
    return w_tuple

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
