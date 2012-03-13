from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.rlib.rarithmetic import intmask
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.slicetype import unwrap_start_stop
from pypy.objspace.std import slicetype
from pypy.interpreter import gateway
from pypy.rlib import jit

# Tuples of known length up to UNROLL_TUPLE_LIMIT have unrolled certain methods
UNROLL_TUPLE_LIMIT = 10

class W_AbstractTupleObject(W_Object):
    __slots__ = ()

    def unwrap(self, space):
        items = [space.unwrap(w_item) for w_item in self.tolist(space)]
        return tuple(items)

    def tolist(self, space):
        "Returns the items, as a fixed-size list."
        raise NotImplementedError

    def getitems_copy(self, space):
        "Returns a copy of the items, as a resizable list."
        raise NotImplementedError

class W_TupleObject(W_AbstractTupleObject):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef

    def __init__(self, tuplestorage):
        self.tuplestorage = tuplestorage

    def tolist(self, space):
        items_w = [None] * self.length()
        for i in xrange(self.length()):
            items_w[i] = self.getitem(space, i)
        return items_w

    def getitems_copy(self, space):
        return self.tolist(space)[:]

    def length(self):
        return self.tuplestorage.getlength()

    def getitem(self, space, i):
        from pypy.objspace.std.tupletype import read_obj

        return read_obj(space, self.tuplestorage, i)

registerimplementation(W_TupleObject)


def len__Tuple(space, w_tuple):
    return space.wrap(w_tuple.length())

def getitem__Tuple_ANY(space, w_tuple, w_index):
    index = space.getindex_w(w_index, space.w_IndexError, "tuple index")
    if index < 0:
        index += w_tuple.length()
    if not (0 <= index < w_tuple.length()):
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))
    return w_tuple.getitem(space, index)

def getitem__Tuple_Slice(space, w_tuple, w_slice):
    length = w_tuple.length()
    start, stop, step, slicelength = w_slice.indices4(space, length)
    return getslice(space, w_tuple, slicelength, start, stop, step)

def getslice(space, w_tuple, slicelength, start, stop, step):
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = w_tuple.getitem(space, start)
        start += step
    return space.newtuple(subitems)

def getslice__Tuple_ANY_ANY(space, w_tuple, w_start, w_stop):
    start, stop = normalize_simple_slice(space, w_tuple.length(), w_start, w_stop)
    return getslice(space, w_tuple, stop - start, start, stop, 1)

def contains__Tuple_ANY(space, w_tuple, w_obj):
    for i in xrange(w_tuple.length()):
        if space.eq_w(w_tuple.getitem(space, i), w_obj):
            return space.w_True
    return space.w_False

def add__Tuple_Tuple(space, w_tuple1, w_tuple2):
    return space.newtuple(w_tuple1.tolist(space) + w_tuple2.tolist(space))

def mul__Tuple_ANY(space, w_tuple, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if times == 1 and space.type(w_tuple) is space.w_tuple:
        return w_tuple
    return space.newtuple(w_tuple.tolist(space) * times)

def mul__ANY_Tuple(space, w_times, w_tuple):
    return mul__Tuple_ANY(space, w_tuple, w_times)

def tuple_unroll_condition(space, w_tuple1, w_tuple2):
    lgt1 = w_tuple1.length()
    lgt2 = w_tuple2.length()
    return ((jit.isconstant(lgt1) and lgt1 <= UNROLL_TUPLE_LIMIT) or
            (jit.isconstant(lgt2) and lgt2 <= UNROLL_TUPLE_LIMIT))

@jit.look_inside_iff(tuple_unroll_condition)
def eq__Tuple_Tuple(space, w_tuple1, w_tuple2):
    if w_tuple1.tuplestorage.getshape() is not w_tuple2.tuplestorage.getshape():
        return space.w_False
    if w_tuple1.length() != w_tuple2.length():
        return space.w_False
    for i in xrange(w_tuple1.length()):
        if not space.eq_w(w_tuple1.getitem(space, i), w_tuple2.getitem(space, i)):
            return space.w_False
    return space.w_True

@jit.look_inside_iff(tuple_unroll_condition)
def lt__Tuple_Tuple(space, w_tuple1, w_tuple2):
    ncmp = min(w_tuple1.length(), w_tuple2.length())
    # Search for the first index where items are different
    for i in range(ncmp):
        w_obj1 = w_tuple1.getitem(space, i)
        w_obj2 = w_tuple2.getitem(space, i)
        if not space.eq_w(w_obj1, w_obj2):
            return space.lt(w_obj1, w_obj2)
    # No more items to compare -- compare sizes
    return space.newbool(w_tuple1.length() < w_tuple2.length())

@jit.look_inside_iff(tuple_unroll_condition)
def gt__Tuple_Tuple(space, w_tuple1, w_tuple2):
    ncmp = min(w_tuple1.length(), w_tuple2.length())
    # Search for the first index where items are different
    for i in range(ncmp):
        w_obj1 = w_tuple1.getitem(space, i)
        w_obj2 = w_tuple2.getitem(space, i)
        if not space.eq_w(w_obj1, w_obj2):
            return space.gt(w_obj1, w_obj2)
    # No more items to compare -- compare sizes
    return space.newbool(w_tuple1.length() > w_tuple2.length())

def repr__Tuple(space, w_tuple):
    repr = "("
    if w_tuple.length() == 1:
        repr += space.str_w(space.repr(w_tuple.getitem(space, 0)))
        repr += ",)"
        return space.wrap(repr)
    repr += ", ".join([space.str_w(space.repr(w_tuple.getitem(space, i))) for i in xrange(w_tuple.length())])
    repr += ")"
    return space.wrap(repr)

@jit.look_inside_iff(lambda space, w_tuple:
                     jit.isconstant(w_tuple.length()) and
                     w_tuple.length() < UNROLL_TUPLE_LIMIT)
def hash__Tuple(space, w_tuple):
    # this is the CPython 2.4 algorithm (changed from 2.3)
    mult = 1000003
    x = 0x345678
    z = w_tuple.length()
    for i in xrange(z):
        y = space.hash_w(w_tuple.getitem(space, i))
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return space.wrap(intmask(x))

def getnewargs__Tuple(space, w_tuple):
    return space.newtuple([space.newtuple(w_tuple.tolist(space))])

def tuple_count__Tuple_ANY(space, w_tuple, w_obj):
    count = 0
    for i in xrange(w_tuple.length()):
        count += space.eq_w(w_tuple.getitem(space, i), w_obj)
    return space.wrap(count)

def tuple_index__Tuple_ANY_ANY_ANY(space, w_tuple, w_obj, w_start, w_stop):
    length = w_tuple.length()
    start, stop = unwrap_start_stop(space, length, w_start, w_stop)

    for i in xrange(start, min(stop, length)):
        w_value = w_tuple.getitem(space, i)
        if space.eq_w(w_value, w_obj):
            return space.wrap(i)

    raise OperationError(space.w_ValueError,
                         space.wrap("tuple.index(x): x not in tuple"))

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)
