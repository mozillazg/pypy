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
from pypy.interpreter.gateway import interp2app, ObjSpace


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
        return space.wrap(self.length())
    descr_len.unwrap_spec = ['self', ObjSpace]


Buffer.typedef = TypeDef(
    "buffer",
    __len__ = interp2app(Buffer.descr_len),
    )

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
