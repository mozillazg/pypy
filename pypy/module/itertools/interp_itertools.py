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
    return space.wrap(W_Count(space, firstval))

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

    def __init__(self, space):
        self.space = space

