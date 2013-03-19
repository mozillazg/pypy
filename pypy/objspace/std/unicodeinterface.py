"""Unicode object interface."""

from pypy.objspace.std.model import W_Object
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from rpython.rlib.objectmodel import compute_unique_id


class W_AbstractUnicodeObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractUnicodeObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return space.unicode_w(self) is space.unicode_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(space.unicode_w(self)))


class UnicodeInterface(object):
    @unwrap_spec(w_self=W_Root, width=int, fillchar=str)
    def ljust(w_self, space, width, fillchar=' '):
        """S.ljust(width[, fillchar]) -> int

        Return S left justified in a Unicode string of length width. Padding is
        done using the specified fill character (default is a space).
        """
        assert isinstance(w_self, W_AbstractUnicodeObject)
        return w_self.ljust(space, width, fillchar)


def unicode_interface_methods():
    return dict((name, interp2app(method)) for
                name, method in UnicodeInterface.__dict__.items()
                if not name.startswith('_'))
