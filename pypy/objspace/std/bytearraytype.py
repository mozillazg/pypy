from pypy.objspace.std.model import W_Object
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import (
    interpindirect2app, interp2app, unwrap_spec)
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM

from pypy.objspace.std.stringtype import (
    str_count, str_index, str_rindex, str_find, str_rfind, str_replace,
    str_startswith, str_endswith, str_islower, str_isupper, str_isalpha,
    str_isalnum, str_isdigit, str_isspace, str_istitle,
    str_upper, str_lower, str_title, str_swapcase, str_capitalize,
    str_expandtabs, str_center, str_zfill,
    str_split, str_rsplit, str_partition, str_rpartition,
    str_splitlines, str_translate)

from rpython.rlib.objectmodel import newlist_hint, resizelist_hint


class W_AbstractBytearrayObject(W_Object):
    @unwrap_spec(arg=int, fillchar=str)
    def descr_ljust(self, space, arg, fillchar=' '):
        """S.ljust(width[, fillchar]) -> string

        Return S left justified in a string of length width. Padding
        is done using the specified fill character (default is a space).
        """
        raise NotImplementedError

    @unwrap_spec(arg=int, fillchar=str)
    def descr_rjust(self, space, arg, fillchar=' '):
        """S.rjust(width[, fillchar]) -> string

        Return S right justified in a string of length width. Padding
        is done using the specified fill character (default is a space).
        """
        raise NotImplementedError

    @unwrap_spec(index=int, val='chr')
    def descr_insert(self, space, index, val):
        """B.insert(index, int) -> None

        Insert a single item into the bytearray before the given index.
        """
        raise NotImplementedError

    @unwrap_spec(index=int)
    def descr_pop(self, space, index=-1):
        """B.pop([index]) -> int

        Remove and return a single item from B. If no index
        argument is given, will pop the last value.
        """
        raise NotImplementedError

    @unwrap_spec(value='index')
    def descr_remove(self, space, value):
        """B.remove(int) -> None

        Remove the first occurance of a value in B.
        """
        raise NotImplementedError

    @unwrap_spec(val='chr')
    def descr_append(self, space, val):
        """B.append(int) -> None

        Append a single item to the end of B.
        """
        raise NotImplementedError

    def descr_extend(self, space, w_iterable):
        """B.extend(iterable int) -> None

        Append all the elements from the iterator or sequence to the
        end of B.
        """
        raise NotImplementedError

    def descr_join(self, space, w_iterable):
        """B.join(iterable_of_bytes) -> bytes

        Concatenates any number of bytearray objects, with B in between each
        pair.
        """
        raise NotImplementedError

    def descr_reverse(self, space):
        """B.reverse() -> None

        Reverse the order of the values in B in place.
        """
        raise NotImplementedError

    def descr_strip(self, space, w_chars=None):
        """B.strip([bytes]) -> bytearray

        Strip leading and trailing bytes contained in the argument.
        If the argument is omitted, strip ASCII whitespace.
        """
        raise NotImplementedError

    def descr_lstrip(self, space, w_chars=None):
        """B.lstrip([bytes]) -> bytearray

        Strip leading bytes contained in the argument.
        If the argument is omitted, strip leading ASCII whitespace.
        """
        raise NotImplementedError

    def descr_rstrip(self, space, w_chars=None):
        """B.rstrip([bytes]) -> bytearray

        Strip trailing bytes contained in the argument.
        If the argument is omitted, strip trailing ASCII whitespace.
        """
        raise NotImplementedError

    def descr_decode(self, space, w_encoding=None, w_errors=None):
        """B.decode([encoding[,errors]]) -> object

        Decodes B using the codec registered for encoding. encoding defaults
        to the default encoding. errors may be given to set a different error
        handling scheme. Default is 'strict' meaning that encoding errors raise
        a UnicodeDecodeError. Other possible values are 'ignore' and 'replace'
        as well as any other name registerd with codecs.register_error that is
        able to handle UnicodeDecodeErrors.
        """
        from pypy.objspace.std.unicodetype import (
            _get_encoding_and_errors, decode_object)
        encoding, errors = _get_encoding_and_errors(
            space, w_encoding, w_errors)
        return decode_object(space, self, encoding, errors)


def getbytevalue(space, w_value):
    if space.isinstance_w(w_value, space.w_str):
        string = space.str_w(w_value)
        if len(string) != 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "string must be of size 1"))
        return string[0]

    value = space.getindex_w(w_value, None)
    if not 0 <= value < 256:
        # this includes the OverflowError in case the long is too large
        raise OperationError(space.w_ValueError, space.wrap(
            "byte must be in range(0, 256)"))
    return chr(value)

def new_bytearray(space, w_bytearraytype, data):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj


def descr__new__(space, w_bytearraytype, __args__):
    return new_bytearray(space,w_bytearraytype, [])


def makebytearraydata_w(space, w_source):
    # String-like argument
    try:
        string = space.bufferstr_new_w(w_source)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        return [c for c in string]

    # sequence of bytes
    w_iter = space.iter(w_source)
    length_hint = space.length_hint(w_source, 0)
    data = newlist_hint(length_hint)
    extended = 0
    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        value = getbytevalue(space, w_item)
        data.append(value)
        extended += 1
    if extended < length_hint:
        resizelist_hint(data, extended)
    return data

def descr_bytearray__reduce__(space, w_self):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    assert isinstance(w_self, W_BytearrayObject)
    w_dict = w_self.getdict(space)
    if w_dict is None:
        w_dict = space.w_None
    return space.newtuple([
        space.type(w_self), space.newtuple([
            space.wrap(''.join(w_self.data).decode('latin-1')),
            space.wrap('latin-1')]),
        w_dict])

def _hex_digit_to_int(d):
    val = ord(d)
    if 47 < val < 58:
        return val - 48
    if 96 < val < 103:
        return val - 87
    return -1

def descr_fromhex(space, w_type, w_hexstring):
    "bytearray.fromhex(string) -> bytearray\n"
    "\n"
    "Create a bytearray object from a string of hexadecimal numbers.\n"
    "Spaces between two numbers are accepted.\n"
    "Example: bytearray.fromhex('B9 01EF') -> bytearray(b'\\xb9\\x01\\xef')."
    hexstring = space.str_w(w_hexstring)
    hexstring = hexstring.lower()
    data = []
    length = len(hexstring)
    i = -2
    while True:
        i += 2
        while i < length and hexstring[i] == ' ':
            i += 1
        if i >= length:
            break
        if i+1 == length:
            raise OperationError(space.w_ValueError, space.wrap(
                "non-hexadecimal number found in fromhex() arg at position %d" % i))

        top = _hex_digit_to_int(hexstring[i])
        if top == -1:
            raise OperationError(space.w_ValueError, space.wrap(
                "non-hexadecimal number found in fromhex() arg at position %d" % i))
        bot = _hex_digit_to_int(hexstring[i+1])
        if bot == -1:
            raise OperationError(space.w_ValueError, space.wrap(
                "non-hexadecimal number found in fromhex() arg at position %d" % (i+1,)))
        data.append(chr(top*16 + bot))

    # in CPython bytearray.fromhex is a staticmethod, so
    # we ignore w_type and always return a bytearray
    return new_bytearray(space, space.w_bytearray, data)

# ____________________________________________________________

bytearray_typedef = StdTypeDef("bytearray",
    __doc__ = '''bytearray() -> an empty bytearray
bytearray(sequence) -> bytearray initialized from sequence\'s items

If the argument is a bytearray, the return value is the same object.''',
    __new__ = interp2app(descr__new__),
    __hash__ = None,
    __reduce__ = interp2app(descr_bytearray__reduce__),
    fromhex = interp2app(descr_fromhex, as_classmethod=True),
    ljust=interpindirect2app(W_AbstractBytearrayObject.descr_ljust),
    rjust=interpindirect2app(W_AbstractBytearrayObject.descr_rjust),
    insert=interpindirect2app(W_AbstractBytearrayObject.descr_insert),
    pop=interpindirect2app(W_AbstractBytearrayObject.descr_pop),
    remove=interpindirect2app(W_AbstractBytearrayObject.descr_remove),
    append=interpindirect2app(W_AbstractBytearrayObject.descr_append),
    extend=interpindirect2app(W_AbstractBytearrayObject.descr_extend),
    join=interpindirect2app(W_AbstractBytearrayObject.descr_join),
    reverse=interpindirect2app(W_AbstractBytearrayObject.descr_reverse),
    strip=interpindirect2app(W_AbstractBytearrayObject.descr_strip),
    lstrip=interpindirect2app(W_AbstractBytearrayObject.descr_lstrip),
    rstrip=interpindirect2app(W_AbstractBytearrayObject.descr_rstrip),
    decode=interpindirect2app(W_AbstractBytearrayObject.descr_decode),
    )
bytearray_typedef.registermethods(globals())
