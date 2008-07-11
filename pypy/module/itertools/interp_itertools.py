from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.rlib.rarithmetic import ovfcheck

class W_Count(Wrappable):

    def __init__(self, space, firstval):
        self.space = space
        self.c = firstval
        self.overflowed = False

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.overflowed:
            raise OperationError(self.space.w_OverflowError,
                    self.space.wrap("cannot count beyond sys.maxint"))

        c = self.c
        try:
            self.c = ovfcheck(self.c + 1)
        except OverflowError:
            self.overflowed = True

        return self.space.wrap(c)


def W_Count___new__(space, w_subtype, firstval=0):
    """
    Create a new count object and call its initializer.
    """
    result = space.allocate_instance(W_Count, w_subtype)
    W_Count.__init__(result, space, firstval)
    return space.wrap(result)

W_Count.typedef = TypeDef(
        'count',
        __new__ = interp2app(W_Count___new__, unwrap_spec=[ObjSpace, W_Root, int]),
        __iter__ = interp2app(W_Count.iter_w, unwrap_spec=['self']),
        next = interp2app(W_Count.next_w, unwrap_spec=['self']),
        __doc__ = """Make an iterator that returns consecutive integers starting
    with n.  If not specified n defaults to zero. Does not currently
    support python long integers. Often used as an argument to imap()
    to generate consecutive data points.  Also, used with izip() to
    add sequence numbers.

    Equivalent to :

    def count(n=0):
        if not isinstance(n, int):
            raise TypeError("%s is not a regular integer" % n)
        while True:
            yield n
            n += 1
    """)


class W_Repeat(Wrappable):

    def __init__(self, space, w_obj, w_times):
        self.space = space
        self.w_obj = w_obj
        
        if space.is_w(w_times, space.w_None):
            self.counting = False
            self.count = 0
        else:
            self.counting = True
            self.count = self.space.int_w(w_times)

    def next_w(self):
        if self.counting:
            if self.count <= 0:
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            self.count -= 1
        return self.w_obj

    def iter_w(self):
        return self.space.wrap(self)

def W_Repeat___new__(space, w_subtype, w_obj, w_times=None):
    """
    Create a new repeat object and call its initializer.
    """
    result = space.allocate_instance(W_Repeat, w_subtype)
    W_Repeat.__init__(result, space, w_obj, w_times)
    return space.wrap(result)

W_Repeat.typedef = TypeDef(
        'repeat',
        __new__  = interp2app(W_Repeat___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root]),
        __iter__ = interp2app(W_Repeat.iter_w, unwrap_spec=['self']),
        next     = interp2app(W_Repeat.next_w, unwrap_spec=['self']),
        __doc__  = """Make an iterator that returns object over and over again.
    Runs indefinitely unless the times argument is specified.  Used
    as argument to imap() for invariant parameters to the called
    function. Also used with izip() to create an invariant part of a
    tuple record.

    Equivalent to :

    def repeat(object, times=None):
        if times is None:
            while True:
                yield object
        else:
            for i in xrange(times):
                yield object
    """)

class W_TakeWhile(Wrappable):

    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)
        self.stopped = False

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.stopped:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        w_obj = self.space.next(self.iterable)  # may raise a w_StopIteration
        w_bool = self.space.call_function(self.w_predicate, w_obj)
        if not self.space.is_true(w_bool):
            self.stopped = True
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        return w_obj

def W_TakeWhile___new__(space, w_subtype, w_predicate, w_iterable):
    result = space.allocate_instance(W_TakeWhile, w_subtype)
    W_TakeWhile.__init__(result, space, w_predicate, w_iterable)
    return space.wrap(result)


W_TakeWhile.typedef = TypeDef(
        'takewhile',
        __new__  = interp2app(W_TakeWhile___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root]),
        __iter__ = interp2app(W_TakeWhile.iter_w, unwrap_spec=['self']),
        next     = interp2app(W_TakeWhile.next_w, unwrap_spec=['self']),
        __doc__  = """Make an iterator that returns elements from the iterable as
    long as the predicate is true.

    Equivalent to :
    
    def takewhile(predicate, iterable):
        for x in iterable:
            if predicate(x):
                yield x
            else:
                break
    """)

class W_DropWhile(Wrappable):

    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)
        self.started = False

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.started:
            w_obj = self.space.next(self.iterable)  # may raise w_StopIteration
        else:
            while True:
                w_obj = self.space.next(self.iterable)  # may raise w_StopIter
                w_bool = self.space.call_function(self.w_predicate, w_obj)
                if not self.space.is_true(w_bool):
                    self.started = True
                    break

        return w_obj

def W_DropWhile___new__(space, w_subtype, w_predicate, w_iterable):
    result = space.allocate_instance(W_DropWhile, w_subtype)
    W_DropWhile.__init__(result, space, w_predicate, w_iterable)
    return space.wrap(result)


W_DropWhile.typedef = TypeDef(
        'dropwhile',
        __new__  = interp2app(W_DropWhile___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root]),
        __iter__ = interp2app(W_DropWhile.iter_w, unwrap_spec=['self']),
        next     = interp2app(W_DropWhile.next_w, unwrap_spec=['self']),
        __doc__  = """Make an iterator that drops elements from the iterable as long
    as the predicate is true; afterwards, returns every
    element. Note, the iterator does not produce any output until the
    predicate is true, so it may have a lengthy start-up time.

    Equivalent to :

    def dropwhile(predicate, iterable):
        iterable = iter(iterable)
        for x in iterable:
            if not predicate(x):
                yield x
                break
        for x in iterable:
            yield x
    """)

class _IFilterBase(Wrappable):

    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        if space.is_w(w_predicate, space.w_None):
            self.w_predicate = space.w_bool
        else:
            self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        while True:
            w_obj = self.space.next(self.iterable)  # may raise w_StopIteration
            w_pred = self.space.call_function(self.w_predicate, w_obj)
            pred = self.space.is_true(w_pred)
            if pred ^ self.reverse:
                return w_obj


class W_IFilter(_IFilterBase):
    reverse = False

def W_IFilter___new__(space, w_subtype, w_predicate, w_iterable):
    result = space.allocate_instance(W_IFilter, w_subtype)
    W_IFilter.__init__(result, space, w_predicate, w_iterable)
    return space.wrap(result)

W_IFilter.typedef = TypeDef(
        'ifilter',
        __new__  = interp2app(W_IFilter___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root]),
        __iter__ = interp2app(W_IFilter.iter_w, unwrap_spec=['self']),
        next     = interp2app(W_IFilter.next_w, unwrap_spec=['self']),
        __doc__  = """Make an iterator that filters elements from iterable returning
    only those for which the predicate is True.  If predicate is
    None, return the items that are true.

    Equivalent to :

    def ifilter:
        if predicate is None:
            predicate = bool
        for x in iterable:
            if predicate(x):
                yield x
    """)

class W_IFilterFalse(_IFilterBase):
    reverse = True

def W_IFilterFalse___new__(space, w_subtype, w_predicate, w_iterable):
    result = space.allocate_instance(W_IFilterFalse, w_subtype)
    W_IFilterFalse.__init__(result, space, w_predicate, w_iterable)
    return space.wrap(result)

W_IFilterFalse.typedef = TypeDef(
        'ifilterfalse',
        __new__  = interp2app(W_IFilterFalse___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root]),
        __iter__ = interp2app(W_IFilterFalse.iter_w, unwrap_spec=['self']),
        next     = interp2app(W_IFilterFalse.next_w, unwrap_spec=['self']),
        __doc__  = """Make an iterator that filters elements from iterable returning
    only those for which the predicate is False.  If predicate is
    None, return the items that are false.

    Equivalent to :
    
    def ifilterfalse(predicate, iterable):
        if predicate is None:
            predicate = bool
        for x in iterable:
            if not predicate(x):
                yield x
    """)

class W_ISlice(Wrappable):
    def __init__(self, space, w_iterable, w_startstop, args_w):
        self.iterable = space.iter(w_iterable)
        self.space = space

        num_args = len(args_w)

        if num_args == 0:
            start = 0
            w_stop = w_startstop
        elif num_args <= 2:
            start = space.int_w(w_startstop)
            w_stop = args_w[0]
        else:
            raise OperationError(space.w_TypeError, space.wrap("islice() takes at most 4 arguments (" + str(num_args) + " given)"))

        if space.is_w(w_stop, space.w_None):
            stop = None
        else:
            stop = space.int_w(w_stop)

        if num_args == 2:
            step = space.int_w(args_w[1])
        else:
            step = 1

        if start < 0:
            raise OperationError(space.w_ValueError, space.wrap("Indicies for islice() must be non-negative integers."))
        if stop is not None and stop < 0:
            raise OperationError(space.w_ValueError, space.wrap("Stop argument must be a non-negative integer or None."))
        if step < 1:
            raise OperationError(space.w_ValueError, space.wrap("Step must be one or lager for islice()."))

        self.start = start
        self.stop = stop
        self.step = step

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.stop is not None and self.stop <= 0:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        if self.start >= 0:
            skip = self.start
            self.start = -1
        else:
            skip = self.step - 1

        while skip > 0:
            self.space.next(self.iterable)
            skip -= 1
            if self.stop is not None:
                self.stop -= 1

        w_obj = self.space.next(self.iterable)
        if self.stop is not None:
            self.stop -= 1
        return w_obj

def W_ISlice___new__(space, w_subtype, w_iterable, w_startstop, args_w):
    result = space.allocate_instance(W_ISlice, w_subtype)
    W_ISlice.__init__(result, space, w_iterable, w_startstop, args_w)
    return space.wrap(result)

W_ISlice.typedef = TypeDef(
        'islice',
        __new__  = interp2app(W_ISlice___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root, 'args_w']),
        __iter__ = interp2app(W_ISlice.iter_w, unwrap_spec=['self']),
        next     = interp2app(W_ISlice.next_w, unwrap_spec=['self']),
        __doc__  = """Make an iterator that returns selected elements from the
    iterable.  If start is non-zero, then elements from the iterable
    are skipped until start is reached. Afterward, elements are
    returned consecutively unless step is set higher than one which
    results in items being skipped. If stop is None, then iteration
    continues until the iterator is exhausted, if at all; otherwise,
    it stops at the specified position. Unlike regular slicing,
    islice() does not support negative values for start, stop, or
    step. Can be used to extract related fields from data where the
    internal structure has been flattened (for example, a multi-line
    report may list a name field on every third line).
    """)

