"""
Buffer protocol support.
"""

# The implementation of the buffer protocol.  The basic idea is that we
# can ask any app-level object for a 'buffer' view on it, by calling its
# __buffer__() special method.  It should return a wrapped instance of a
# subclass of the Buffer class defined below.  Note that __buffer__() is
# a PyPy-only extension to the Python language, made necessary by the
# fact that it's not natural in PyPy to hack an interp-level-only
# interface.

# In normal usage, the convenience method space.buffer_w() should be
# used to get directly a Buffer instance.  Doing so also gives you for
# free the typecheck that __buffer__() really returned a wrapped Buffer.

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError


class Buffer(Wrappable):
    """Abstract base class for memory views."""

    __slots__ = ('len',)     # the length, stored as an attribute

    def as_str(self):
        "Returns an interp-level string with the whole content of the buffer."
        # May be overridden.
        return self.getslice(0, self.length())

    def getitem(self, index):
        "Returns the index'th character in the buffer."
        raise NotImplementedError   # Must be overriden.  No bounds checks.

    def getslice(self, start, stop):
        # May be overridden.  No bounds checks.
        return ''.join([self.getitem(i) for i in range(start, stop)])

    # __________ app-level support __________

    def descr_len(self, space):
        return space.wrap(self.len)
    descr_len.unwrap_spec = ['self', ObjSpace]

    def descr_getitem(self, space, w_index):
        start, stop, step = space.decode_index(w_index, self.len)
        if step == 0:  # index only
            return space.wrap(self.getitem(start))
        elif step == 1:
            if 0 <= start <= stop:
                res = self.getslice(start, stop)
            else:
                res = ''
            return space.wrap(res)
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap("buffer object does not support"
                                            " slicing with a step"))
    descr_getitem.unwrap_spec = ['self', ObjSpace, W_Root]

    def descr__buffer__(self, space):
        return space.wrap(self)
    descr__buffer__.unwrap_spec = ['self', ObjSpace]

    def descr_str(self, space):
        return space.wrap(self.as_str())
    descr_str.unwrap_spec = ['self', ObjSpace]

    def descr_add(self, space, other):
        return space.wrap(self.as_str() + other)
    descr_add.unwrap_spec = ['self', ObjSpace, 'bufferstr']


def descr_buffer__new__(space, w_subtype, w_object):  #, offset, size
    # w_subtype can only be exactly 'buffer' for now
    if not space.is_w(w_subtype, space.gettypefor(Buffer)):
        raise OperationError(space.w_TypeError,
                             space.wrap("argument 1 must be 'buffer'"))
    w_buffer = space.buffer(w_object)
    space.interp_w(Buffer, w_buffer)    # type-check
    return w_buffer
descr_buffer__new__.unwrap_spec = [ObjSpace, W_Root, W_Root]


Buffer.typedef = TypeDef(
    "buffer",
    __doc__ = """\
buffer(object [, offset[, size]])

Create a new buffer object which references the given object.
The buffer will reference a slice of the target object from the
start of the object (or at the specified offset). The slice will
extend to the end of the target object (or with the specified size).
""",
    __new__ = interp2app(descr_buffer__new__),
    __len__ = interp2app(Buffer.descr_len),
    __getitem__ = interp2app(Buffer.descr_getitem),
    __buffer__ = interp2app(Buffer.descr__buffer__),
    __str__ = interp2app(Buffer.descr_str),
    __add__ = interp2app(Buffer.descr_add),
    )
Buffer.typedef.acceptable_as_base_class = False

# ____________________________________________________________

class StringBuffer(Buffer):

    def __init__(self, value):
        self.len = len(value)
        self.value = value

    def as_str(self):
        return self.value

    def getitem(self, index):
        return self.value[index]

    def getslice(self, start, stop):
        assert 0 <= start <= stop <= self.len
        return self.value[start:stop]
