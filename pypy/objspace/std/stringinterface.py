"""String object interface."""

from pypy.objspace.std.contiguousstring import W_AbstractStringObject
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec


class StringInterface(object):
    @unwrap_spec(w_self=W_Root, arg=int, fillchar=str)
    def ljust(w_self, space, arg, fillchar=' '):
        """S.ljust(width[, fillchar]) -> string

        Return S left justified in a string of length width. Padding
        is done using the specified fill character (default is a space).
        """
        assert isinstance(w_self, W_AbstractStringObject)
        return w_self.ljust(space, arg, fillchar)


def string_interface_methods():
    return dict((name, interp2app(method)) for
                name, method in StringInterface.__dict__.items()
                if not name.startswith('_'))
