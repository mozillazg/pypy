"""Common methods for string types (bytes and unicode)"""

from pypy.objspace.std.model import W_Object
from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import compute_unique_id


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


class StringMethods(object):
    _mixin_ = True

    def ljust(self, space, arg, fillchar=' '):
        u_self = self._value
        if len(fillchar) != 1:
            raise OperationError(space.w_TypeError,
                space.wrap("ljust() argument 2 must be a single character"))

        d = arg - len(u_self)
        if d > 0:
            fillchar = fillchar[0]    # annotator hint: it's a single character
            u_self += d * fillchar

        return space.wrap(u_self)
