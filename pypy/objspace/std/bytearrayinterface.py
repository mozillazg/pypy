from pypy.objspace.std.model import W_Object
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec


class W_AbstractBytearrayObject(W_Object):
    pass


class ByteArrayInterface(object) :
    @unwrap_spec(w_self=W_Root, arg=int, fillchar=str)
    def ljust(w_self, space, arg, fillchar=' '):
        """S.ljust(width[, fillchar]) -> string

        Return S left justified in a string of length width. Padding
        is done using the specified fill character (default is a space).
        """
        u_self = w_self.data
        assert isinstance(w_self, W_AbstractBytearrayObject)
        if len(fillchar) != 1:
            raise OperationError(space.w_TypeError,
                space.wrap("ljust() argument 2 must be a single character"))

        d = arg - len(u_self)
        if d > 0:
            lst = [0] * max(arg, len(u_self))
            fillchar = fillchar[0]    # annotator hint: it's a single character
            lst[:len(u_self)] = u_self
            for i in range(d):
                lst[len(u_self) + i] = fillchar
        else:
            lst = u_self.data[:]

        return space.newbytearray(lst)


def bytearray_interface_methods():
    return dict((name, interp2app(method)) for
                name, method in ByteArrayInterface.__dict__.items()
                if not name.startswith('_'))
