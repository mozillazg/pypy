import sys

from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.rlib.rerased_raw import UntypedStorage, INT, BOOL, INSTANCE
from pypy.rlib.unroll import unrolling_iterable


MAXIMUM_SPECIALIZED_SIZE = 8

def wraptuple(space, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject

    w_tuple = space.allocate_instance(W_TupleObject, space.w_tuple)
    make_tuple(space, w_tuple, list_w)
    return w_tuple

def _check_int(space, w_obj):
    return space.is_w(space.type(w_obj), space.w_int)
def _store_int(space, storage, idx, w_obj):
    storage.setint(idx, space.int_w(w_obj))
def _get_int(space, storage, idx):
    return space.wrap(storage.getint(idx))

def _check_bool(space, w_obj):
    return space.is_w(space.type(w_obj), space.w_bool)
def _store_bool(space, storage, idx, w_obj):
    storage.setbool(idx, space.is_true(w_obj))
def _get_bool(space, storage, idx):
    return space.wrap(storage.getbool(idx))

def _check_instance(space, w_obj):
    return True
def _store_instance(space, storage, idx, w_obj):
    storage.setinstance(idx, w_obj)
def _get_instance(space, storage, idx):
    return storage.getinstance(idx, W_Root)

SPECIALIZED_TYPES = unrolling_iterable([
    (INT, _check_int, _store_int, _get_int),
    (BOOL, _check_bool, _store_bool, _get_bool),
    (INSTANCE, _check_instance, _store_instance, _get_instance)
])

def get_char_from_obj(space, w_obj):
    for char, check, store, read in SPECIALIZED_TYPES:
        if check(space, w_obj):
            return char
    assert False

def store_obj(space, storage, shape_char, idx, w_obj):
    for char, check, store, read in SPECIALIZED_TYPES:
        if shape_char == char:
            store(space, storage, idx, w_obj)
            return
    assert False

def read_obj(space, storage, idx):
    shape_char = storage.getshape()[idx]
    for char, check, store, read in SPECIALIZED_TYPES:
        if shape_char == char:
            return read(space, storage, idx)
    assert False

def make_tuple(space, w_tuple, list_w):
    from pypy.objspace.std.tupleobject import W_TupleObject

    shape_chars = ["\x00"] * len(list_w)
    for i, w_item in enumerate(list_w):
        shape_chars[i] = get_char_from_obj(space, w_item)

    shape = space.str_w(space.new_interned_str("".join(shape_chars)))
    storage = UntypedStorage(shape)
    for i, w_item in enumerate(list_w):
        store_obj(space, storage, shape[i], i, w_item)
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
