"""Common methods for string types (bytes and unicode)"""

from rpython.rlib import jit
from pypy.interpreter.error import OperationError, operationerrfmt
from rpython.rlib.rstring import StringBuilder, split


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

    def rjust(self, space, arg, fillchar=' '):
        u_self = self._value
        if len(fillchar) != 1:
            raise OperationError(space.w_TypeError,
                space.wrap("rjust() argument 2 must be a single character"))

        d = arg - len(u_self)
        if d>0:
            fillchar = fillchar[0]    # annotator hint: it's a single character
            u_self = d * fillchar + u_self

        return space.wrap(u_self)

    def join(self, space, w_list):
        l = space.listview_str(w_list)
        if l is not None:
            if len(l) == 1:
                return space.wrap(l[0])
            return space.wrap(self._value.join(l))
        list_w = space.listview(w_list)
        size = len(list_w)

        if size == 0:
            return space.wrap("")

        if size == 1:
            w_s = list_w[0]
            # only one item,  return it if it's not a subclass of str
            if (space.is_w(space.type(w_s), space.w_str) or
                space.is_w(space.type(w_s), space.w_unicode)):
                return w_s

        return _str_join_many_items(space, self, list_w, size)


@jit.look_inside_iff(lambda space, w_self, list_w, size:
                     jit.loop_unrolling_heuristic(list_w, size))
def _str_join_many_items(space, w_self, list_w, size):
    self = w_self._value
    reslen = len(self) * (size - 1)
    for i in range(size):
        w_s = list_w[i]
        if not space.isinstance_w(w_s, space.w_str):
            if space.isinstance_w(w_s, space.w_unicode):
                # we need to rebuild w_list here, because the original
                # w_list might be an iterable which we already consumed
                w_list = space.newlist(list_w)
                w_u = space.call_function(space.w_unicode, w_self)
                return space.call_method(w_u, "join", w_list)
            raise operationerrfmt(
                space.w_TypeError,
                "sequence item %d: expected string, %s "
                "found", i, space.type(w_s).getname(space))
        reslen += len(space.str_w(w_s))

    sb = StringBuilder(reslen)
    for i in range(size):
        if self and i != 0:
            sb.append(self)
        sb.append(space.str_w(list_w[i]))
    return space.wrap(sb.build())