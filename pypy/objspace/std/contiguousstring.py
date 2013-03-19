"""Common methods for string types (bytes and unicode)"""

from pypy.interpreter.error import OperationError


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
