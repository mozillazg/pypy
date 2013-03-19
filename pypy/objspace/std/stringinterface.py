"""String object interface."""

from pypy.objspace.std.model import W_Object
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from rpython.rlib.objectmodel import compute_unique_id
from pypy.interpreter.error import OperationError


class W_AbstractStringObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractStringObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return space.str_w(self) is space.str_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(space.str_w(self)))

    def unicode_w(w_self, space):
        # Use the default encoding.
        from pypy.objspace.std.unicodetype import unicode_from_string, \
                decode_object
        w_defaultencoding = space.call_function(space.sys.get(
                                                'getdefaultencoding'))
        from pypy.objspace.std.unicodetype import _get_encoding_and_errors, \
            unicode_from_string, decode_object
        encoding, errors = _get_encoding_and_errors(space, w_defaultencoding,
                                                    space.w_None)
        if encoding is None and errors is None:
            return space.unicode_w(unicode_from_string(space, w_self))
        return space.unicode_w(decode_object(space, w_self, encoding, errors))


class StringInterface(object):
    @unwrap_spec(w_self=W_Root)
    def join(w_self, space, w_list):
        """S.join(sequence) -> string

        Return a string which is
        the concatenation of the strings in the sequence.
        The separator between elements is S."""
        assert isinstance(w_self, W_AbstractStringObject)
        return w_self.join(space, w_list)

    @unwrap_spec(w_self=W_Root, arg=int, fillchar=str)
    def ljust(w_self, space, arg, fillchar=' '):
        """S.ljust(width[, fillchar]) -> string

        Return S left justified in a string of length width. Padding
        is done using the specified fill character (default is a space).
        """
        assert isinstance(w_self, W_AbstractStringObject)
        return w_self.ljust(space, arg, fillchar)

    @unwrap_spec(w_self=W_Root, arg=int, fillchar=str)
    def rjust(w_self, space, arg, fillchar=' '):
        """S.rjust(width[, fillchar]) -> string

        Return S
        right justified in a string of length width.
        Padding is done using the specified fill character
        (default is a space)"""
        assert isinstance(w_self, W_AbstractStringObject)
        return w_self.rjust(space, arg, fillchar)


def string_interface_methods():
    return dict((name, interp2app(method)) for
                name, method in StringInterface.__dict__.items()
                if not name.startswith('_'))

