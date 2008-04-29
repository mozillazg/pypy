
""" Multituple implementation
"""

from pypy.objspace.std.objspace import *
from pypy.objspace.std.inttype import wrapint
from pypy.rlib.rarithmetic import intmask
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.interpreter import gateway

class BaseTupleImplementation(object):
    size = -1 # interface definition goes here

    def get(self, index):
        raise NotImplementedError

    def getitems(self):
        raise NotImplementedError

    def contains(self, space, w_obj):
        raise NotImplementedError

    def eq(self, space, impl):
        raise NotImplementedError

    def repr(self, space):
        raise NotImplementedError

    def hash(self, space):
        raise NotImplementedError

class EmptyTupleImplementation(BaseTupleImplementation):
    size = 0

    def get(self, index):
        raise IndexError

    def getitems(self):
        return []

    def contains(self, space, w_obj):
        return space.w_False

    def eq(self, space, impl):
        return space.w_True

    def repr(self, space):
        return space.wrap("()")

    def hash(self, space):
        return space.wrap(3527539)

class SingleTupleImplementation(BaseTupleImplementation):
    size = 1

    def __init__(self, w_item):
        self.w_item = w_item

    def get(self, index):
        assert index == 0
        return self.w_item

    def getitems(self):
        return [self.w_item]

    def contains(self, space, w_obj):
        return space.eq(w_obj, self.w_item)

    def eq(self, space, impl):
        assert isinstance(impl, SingleTupleImplementation)
        return space.eq(self.w_item, impl.w_item)

    def repr(self, space):
        return space.wrap("(" + space.str_w(space.repr(self.w_item)) + ",)")

    def hash(self, space):
        mult = 1000003
        x = 0x345678
        y = space.int_w(space.hash(self.w_item))
        x = (x ^ y) * mult
        mult += 82520
        x += 97531
        return space.wrap(intmask(x))

class DoubleTupleImplementation(BaseTupleImplementation):
    size = 2

    def __init__(self, w_item1, w_item2):
        self.w_item1 = w_item1
        self.w_item2 = w_item2

    def get(self, index):
        assert index < 2
        if index == 1:
            return self.w_item2
        return self.w_item1

    def getitems(self):
        return [self.w_item1, self.w_item2]

    def contains(self, space, w_obj):
        return space.newbool(space.eq_w(self.w_item1, w_obj) or
                             space.eq_w(self.w_item2, w_obj))

    def eq(self, space, impl):
        assert isinstance(impl, DoubleTupleImplementation)
        return space.newbool(space.eq_w(self.w_item1, impl.w_item1) and
                             space.eq_w(self.w_item2, impl.w_item2))

    def repr(self, space):
        return space.wrap("(" + space.str_w(space.repr(self.w_item1)) + ", "
                          + space.str_w(space.repr(self.w_item2)) + ")")

    def hash(self, space):
        mult = 1000003
        x = 0x345678
        y = space.int_w(space.hash(self.w_item1))
        x = (x ^ y) * mult
        mult += 82522
        y = space.int_w(space.hash(self.w_item2))
        x = (x ^ y) * mult
        mult += 82520
        x += 97531
        return space.wrap(intmask(x))

class TripleTupleImplementation(BaseTupleImplementation):
    size = 3

    def __init__(self, w_item1, w_item2, w_item3):
        self.w_item1 = w_item1
        self.w_item2 = w_item2
        self.w_item3 = w_item3

    def get(self, index):
        assert index < 3
        if index == 2:
            return self.w_item3
        elif index == 1:
            return self.w_item2
        return self.w_item1

    def getitems(self):
        return [self.w_item1, self.w_item2, self.w_item3]

    def contains(self, space, w_obj):
        return space.newbool(space.eq_w(self.w_item1, w_obj) or
                             space.eq_w(self.w_item2, w_obj) or
                             space.eq_w(self.w_item3, w_obj))

    def eq(self, space, impl):
        assert isinstance(impl, TripleTupleImplementation)
        return space.newbool(space.eq_w(self.w_item1, impl.w_item1) and
                             space.eq_w(self.w_item2, impl.w_item2) and
                             space.eq_w(self.w_item3, impl.w_item3))

    def repr(self, space):
        return space.wrap("(" + space.str_w(space.repr(self.w_item1)) + ", "
                          + space.str_w(space.repr(self.w_item2)) + ", " +
                          space.str_w(space.repr(self.w_item3)) + ")")

    def hash(self, space):
        mult = 1000003
        x = 0x345678
        y = space.int_w(space.hash(self.w_item1))
        x = (x ^ y) * mult
        mult += 82524
        y = space.int_w(space.hash(self.w_item2))
        x = (x ^ y) * mult
        mult += 82522
        y = space.int_w(space.hash(self.w_item3))
        x = (x ^ y) * mult
        mult += 82520
        x += 97531
        return space.wrap(intmask(x))    

class BigTupleImplementation(BaseTupleImplementation):
    def __init__(self, wrappeditems):
        self.size = len(wrappeditems)
        self.wrappeditems = wrappeditems

    def get(self, index):
        return self.wrappeditems[index]

    def getitems(self):
        return self.wrappeditems

    def contains(self, space, w_obj):
        for w_item in self.wrappeditems:
            if space.eq_w(w_item, w_obj):
                return space.w_True
        return space.w_False

    def eq(self, space, impl):
        assert isinstance(impl, BigTupleImplementation)
        items1 = self.wrappeditems
        items2 = impl.wrappeditems
        for i in range(len(items1)):
            item1 = items1[i]
            item2 = items2[i]
            if not space.eq_w(item1, item2):
                return space.w_False
        return space.w_True

    def hash(self, space):
        mult = 1000003
        x = 0x345678
        z = len(self.wrappeditems)
        for w_item in self.wrappeditems:
            y = space.int_w(space.hash(w_item))
            x = (x ^ y) * mult
            z -= 1
            mult += 82520 + z + z
        x += 97531
        return space.wrap(intmask(x))

    def repr(self, space):
        items = self.wrappeditems
        return space.wrap("(" +
                 (", ".join([space.str_w(space.repr(item)) for item in items]))
                          + ")")
        

empty_tuple = EmptyTupleImplementation()

class W_TupleMultiObject(W_Object):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef
    
    def __init__(w_self, wrappeditems):
        lgt = len(wrappeditems)
        if lgt == 0:
            w_self.implementation = empty_tuple
        elif lgt == 1:
            w_self.implementation = SingleTupleImplementation(wrappeditems[0])
        elif lgt == 2:
            w_self.implementation = DoubleTupleImplementation(wrappeditems[0],
                                                              wrappeditems[1])
        elif lgt == 3:
            w_self.implementation = TripleTupleImplementation(wrappeditems[0],
                                                              wrappeditems[1],
                                                              wrappeditems[2])
        else:
            w_self.implementation = BigTupleImplementation(wrappeditems)

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.wrappeditems]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

    def unwrap(w_tuple, space):
        items = [space.unwrap(w_item) for w_item in w_tuple.getitems()] # XXX generic mixed types unwrap
        return tuple(items)

    def getitems(self):
        return self.implementation.getitems()

registerimplementation(W_TupleMultiObject)


def len__TupleMulti(space, w_tuple):
    return wrapint(space, w_tuple.implementation.size)

def getitem__TupleMulti_ANY(space, w_tuple, w_index):
    # getindex_w should get a second argument space.w_IndexError,
    # but that doesn't exist the first time this is called.
    try:
        w_IndexError = space.w_IndexError
    except AttributeError:
        w_IndexError = None
    index = space.getindex_w(w_index, w_IndexError, "tuple index")
    impl = w_tuple.implementation
    if impl.size <= index:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))
    return impl.get(index)
        
def getitem__TupleMulti_Slice(space, w_tuple, w_slice):
    # XXX eventually optimize this
    length = w_tuple.implementation.size
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = w_tuple.implementation.get(start)
        start += step
    return W_TupleMultiObject(subitems)

def contains__TupleMulti_ANY(space, w_tuple, w_obj):
    return w_tuple.implementation.contains(space, w_obj)

def iter__TupleMulti(space, w_tuple):
    from pypy.objspace.std import iterobject
    return iterobject.W_FastSeqIterObject(w_tuple, w_tuple.getitems())

def add__TupleMulti_TupleMulti(space, w_tuple1, w_tuple2):
    items1 = w_tuple1.getitems()
    items2 = w_tuple2.getitems()
    return W_TupleMultiObject(items1 + items2)

def mul_tuple_times(space, w_tuple, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    items = w_tuple.getitems()
    return W_TupleMultiObject(items * times)    

def mul__TupleMulti_ANY(space, w_tuple, w_times):
    return mul_tuple_times(space, w_tuple, w_times)

def mul__ANY_TupleMulti(space, w_times, w_tuple):
    return mul_tuple_times(space, w_tuple, w_times)

def eq__TupleMulti_TupleMulti(space, w_tuple1, w_tuple2):
    if w_tuple1.implementation.size != w_tuple2.implementation.size:
        return space.w_False
    return w_tuple1.implementation.eq(space, w_tuple2.implementation)

def _min(a, b):
    if a < b:
        return a
    return b

def lt__TupleMulti_TupleMulti(space, w_tuple1, w_tuple2):
    # XXX optimize
    items1 = w_tuple1.getitems()
    items2 = w_tuple2.getitems()
    ncmp = _min(len(items1), len(items2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if not space.eq_w(items1[p], items2[p]):
            return space.lt(items1[p], items2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(items1) < len(items2))

def gt__TupleMulti_TupleMulti(space, w_tuple1, w_tuple2):
    # XXX optimize
    items1 = w_tuple1.getitems()
    items2 = w_tuple2.getitems()
    ncmp = _min(len(items1), len(items2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if not space.eq_w(items1[p], items2[p]):
            return space.gt(items1[p], items2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(items1) > len(items2))

def repr__TupleMulti(space, w_tuple):
    return w_tuple.implementation.repr(space)

def hash__TupleMulti(space, w_tuple):
    # this is the CPython 2.4 algorithm (changed from 2.3)
    return w_tuple.implementation.hash(space)

def getnewargs__TupleMulti(space, w_tuple):
    return space.newtuple([W_TupleMultiObject(w_tuple.getitems())])

register_all(vars())

