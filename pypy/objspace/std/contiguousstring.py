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


def unicode_ljust__Unicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._value
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - len(self)
    if padding < 0:
        return w_self.create_if_subclassed()
    result = [fillchar] * width
    for i in range(len(self)):
        result[i] = self[i]
    return W_UnicodeObject(u''.join(result))
