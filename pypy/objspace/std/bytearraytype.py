import sys

from pypy.interpreter import gateway
from pypy.interpreter.argument import Signature
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std import stringobject, slicetype
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import (_delitem_slice_helper,
    _setitem_slice_helper, get_positive_index, get_list_index)
from pypy.objspace.std.model import registerimplementation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.stringtype import (str_decode, str_count, str_index,
    str_rindex, str_find, str_rfind, str_replace, str_startswith, str_endswith,
    str_islower, str_isupper, str_isalpha, str_isalnum, str_isdigit,
    str_isspace, str_istitle, str_upper, str_lower, str_title, str_swapcase,
    str_capitalize, str_expandtabs, str_ljust, str_rjust, str_center,
    str_zfill, str_join, str_split, str_rsplit, str_partition, str_rpartition,
    str_splitlines, str_translate)
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.rlib.rstring import StringBuilder
from pypy.tool.sourcetools import func_with_new_name


_space_chars = ''.join([chr(c) for c in [9, 10, 11, 12, 13, 32]])

class W_BytearrayObject(Wrappable):
    def __init__(w_self, data):
        w_self.data = data

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, ''.join(w_self.data))

    def _strip(self, space, w_chars, left, right):
        if not space.is_w(w_chars, space.w_None):
            chars = space.bufferstr_new_w(w_chars)
        else:
            chars = _space_chars

        s = self.data
        lpos = 0
        rpos = len(s)

        if left:
            while lpos < rpos and s[lpos] in chars:
                lpos += 1

        if right:
            while rpos > lpos and s[rpos - 1] in chars:
                rpos -= 1
            assert rpos >= 0
        return new_bytearray(space, space.w_bytearray, s[lpos:rpos])

    def descr__new__(space, w_subtype, __args__):
        return new_bytearray(space, w_subtype, [])

    def descr__reduce__(self, space):
        w_dict = self.getdict(space)
        if w_dict is None:
            w_dict = space.w_None
        return space.newtuple([
            space.type(self),
            space.newtuple([
                space.wrap(''.join(self.data).decode('latin-1')),
                space.wrap('latin-1')
            ]),
            w_dict
        ])

    @gateway.unwrap_spec(idx=int)
    def descr_insert(self, space, idx, w_other):
        """B.insert(index, int) -> None

        Insert a single item into the bytearray before
        the given index."""
        length = len(self.data)
        index = get_positive_index(idx, length)
        val = getbytevalue(space, w_other)
        self.data.insert(index, val)

    def descr_strip(self, space, w_chars=None):
        return self._strip(space, w_chars, True, True)

    def descr_lstrip(self, space, w_chars=None):
        """B.lstrip([bytes]) -> bytearray

        Strip leading bytes contained in the argument.
        If the argument is omitted, strip leading ASCII whitespace."""
        return self._strip(space, w_chars, True, False)

    def descr_rstrip(self, space, w_chars=None):
        """'B.rstrip([bytes]) -> bytearray

        Strip trailing bytes contained in the argument.
        If the argument is omitted, strip trailing ASCII whitespace."""
        return self._strip(space, w_chars, False, True)

    def descr_append(self, space, w_item):
        self.data.append(getbytevalue(space, w_item))

    def descr_extend(self, space, w_other):
        if space.isinstance_w(w_other, space.w_bytearray):
            self.data += w_other.data
        else:
            self.data += makebytearraydata_w(space, w_other)

    @gateway.unwrap_spec(idx=int)
    def descr_pop(self, space, idx=-1):
        """B.pop([index]) -> int

        Remove and return a single item from B. If no index
        argument is given, will pop the last value."""
        try:
            result = self.data.pop(idx)
        except IndexError:
            if not self.data:
                raise OperationError(space.w_OverflowError, space.wrap(
                    "cannot pop an empty bytearray"))
            raise OperationError(space.w_IndexError, space.wrap(
                "pop index out of range"))
        return space.wrap(ord(result))

    @gateway.unwrap_spec(char="index")
    def descr_remove(self, space, char):
        """B.remove(int) -> None

        Remove the first occurance of a value in B."""
        try:
            self.data.remove(chr(char))
        except ValueError:
            raise OperationError(space.w_ValueError, space.wrap(
                "value not found in bytearray"))

    def descr_reverse(self):
        """B.reverse() -> None

        Reverse the order of the values in B in place."""
        self.data.reverse()



class BytearrayBuffer(RWBuffer):
    def __init__(self, data):
        self.data = data

    def getlength(self):
        return len(self.data)

    def getitem(self, index):
        return self.data[index]

    def setitem(self, index, char):
        self.data[index] = char


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
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj


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
    data = []
    w_iter = space.iter(w_source)
    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        value = getbytevalue(space, w_item)
        data.append(value)
    return data

def _hex_digit_to_int(d):
    val = ord(d)
    if 47 < val < 58:
        return val - 48
    if 96 < val < 103:
        return val - 87
    return -1

def descr_fromhex(space, w_type, w_hexstring):
    "bytearray.fromhex(string) -> bytearray\n\nCreate a bytearray object "
    "from a string of hexadecimal numbers.\nSpaces between two numbers are "
    "accepted.\nExample: bytearray.fromhex('B9 01EF') -> "
    "bytearray(b'\\xb9\\x01\\xef')."
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

### MULTIMETHODS: KILL THEM

registerimplementation(W_BytearrayObject)


init_signature = Signature(['source', 'encoding', 'errors'], None, None)
init_defaults = [None, None, None]

def init__Bytearray(space, w_bytearray, __args__):
    # this is on the silly side
    w_source, w_encoding, w_errors = __args__.parse_obj(
            None, 'bytearray', init_signature, init_defaults)

    if w_source is None:
        w_source = space.wrap('')
    if w_encoding is None:
        w_encoding = space.w_None
    if w_errors is None:
        w_errors = space.w_None

    # Unicode argument
    if not space.is_w(w_encoding, space.w_None):
        from pypy.objspace.std.unicodetype import (
            _get_encoding_and_errors, encode_object
        )
        encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)

        # if w_source is an integer this correctly raises a TypeError
        # the CPython error message is: "encoding or errors without a string argument"
        # ours is: "expected unicode, got int object"
        w_source = encode_object(space, w_source, encoding, errors)

    # Is it an int?
    try:
        count = space.int_w(w_source)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        if count < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("bytearray negative count"))
        w_bytearray.data = ['\0'] * count
        return

    data = makebytearraydata_w(space, w_source)
    w_bytearray.data = data

def str__Bytearray(space, w_bytearray):
    return space.wrap(''.join(w_bytearray.data))

def eq__Bytearray_String(space, w_bytearray, w_other):
    return space.eq(str__Bytearray(space, w_bytearray), w_other)

def eq__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    if len(data1) != len(data2):
        return space.w_False
    for i in range(len(data1)):
        if data1[i] != data2[i]:
            return space.w_False
    return space.w_True

def len__Bytearray(space, w_bytearray):
    result = len(w_bytearray.data)
    return space.wrap(result)

# Mostly copied from repr__String, but without the "smart quote"
# functionality.
def repr__Bytearray(space, w_bytearray):
    s = w_bytearray.data

    # Good default for the common case of no special quoting.
    buf = StringBuilder(len("bytearray(b'')") + len(s))

    buf.append("bytearray(b'")

    for i in range(len(s)):
        c = s[i]

        if c == '\\' or c == "'":
            buf.append('\\')
            buf.append(c)
        elif c == '\t':
            buf.append('\\t')
        elif c == '\r':
            buf.append('\\r')
        elif c == '\n':
            buf.append('\\n')
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            buf.append('\\x')
            buf.append("0123456789abcdef"[n>>4])
            buf.append("0123456789abcdef"[n&0xF])
        else:
            buf.append(c)

    buf.append("')")

    return space.wrap(buf.build())

def getitem__Bytearray_ANY(space, w_bytearray, w_index):
    # getindex_w should get a second argument space.w_IndexError,
    # but that doesn't exist the first time this is called.
    try:
        w_IndexError = space.w_IndexError
    except AttributeError:
        w_IndexError = None
    index = space.getindex_w(w_index, w_IndexError, "bytearray index")
    try:
        return space.newint(ord(w_bytearray.data[index]))
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("bytearray index out of range"))

def delitem__Bytearray_ANY(space, w_bytearray, w_idx):
    idx = get_list_index(space, w_idx)
    try:
        del w_bytearray.data[idx]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("bytearray deletion index out of range"))
    return space.w_None

def getitem__Bytearray_Slice(space, w_bytearray, w_slice):
    data = w_bytearray.data
    length = len(data)
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    newdata = [data[start + i*step] for i in range(slicelength)]
    return W_BytearrayObject(newdata)

def setitem__Bytearray_ANY_ANY(space, w_bytearray, w_index, w_item):
    from pypy.objspace.std.bytearraytype import getbytevalue
    idx = space.getindex_w(w_index, space.w_IndexError, "bytearray index")
    try:
        w_bytearray.data[idx] = getbytevalue(space, w_item)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("bytearray index out of range"))

def setitem__Bytearray_Slice_ANY(space, w_bytearray, w_slice, w_other):
    oldsize = len(w_bytearray.data)
    start, stop, step, slicelength = w_slice.indices4(space, oldsize)
    sequence2 = makebytearraydata_w(space, w_other)
    setitem_slice_helper(space, w_bytearray.data, start, step, slicelength, sequence2, empty_elem='\x00')

def delitem__Bytearray_Slice(space, w_bytearray, w_slice):
    start, stop, step, slicelength = w_slice.indices4(space,
                                                      len(w_bytearray.data))
    delitem_slice_helper(space, w_bytearray.data, start, step, slicelength)

# create new helper functions with different list type specialisation
delitem_slice_helper = func_with_new_name(_delitem_slice_helper,
                                          'delitem_slice_helper')
setitem_slice_helper = func_with_new_name(_setitem_slice_helper,
                                          'setitem_slice_helper')

def add__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    return W_BytearrayObject(data1 + data2)

def add__Bytearray_ANY(space, w_bytearray1, w_other):
    data1 = w_bytearray1.data
    data2 = [c for c in space.bufferstr_new_w(w_other)]
    return W_BytearrayObject(data1 + data2)

def add__String_Bytearray(space, w_str, w_bytearray):
    data2 = w_bytearray.data
    data1 = [c for c in space.str_w(w_str)]
    return W_BytearrayObject(data1 + data2)

def inplace_add__Bytearray_ANY(space, w_bytearray1, w_iterable2):
    w_bytearray1.data += space.bufferstr_new_w(w_iterable2)
    return w_bytearray1

def mul_bytearray_times(space, w_bytearray, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    data = w_bytearray.data
    return W_BytearrayObject(data * times)

def mul__Bytearray_ANY(space, w_bytearray, w_times):
    return mul_bytearray_times(space, w_bytearray, w_times)

def mul__ANY_Bytearray(space, w_times, w_bytearray):
    return mul_bytearray_times(space, w_bytearray, w_times)

def inplace_mul__Bytearray_ANY(space, w_bytearray, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    w_bytearray.data *= times
    return w_bytearray

def contains__Bytearray_ANY(space, w_bytearray, w_sub):
    # XXX slow - copies, needs rewriting
    w_str = space.wrap(space.bufferstr_new_w(w_sub))
    w_str2 = str__Bytearray(space, w_bytearray)
    return stringobject.contains__String_String(space, w_str2, w_str)

def contains__Bytearray_String(space, w_bytearray, w_str):
    # XXX slow - copies, needs rewriting
    w_str2 = str__Bytearray(space, w_bytearray)
    return stringobject.contains__String_String(space, w_str2, w_str)

def contains__Bytearray_Int(space, w_bytearray, w_char):
    char = space.int_w(w_char)
    if not 0 <= char < 256:
        raise OperationError(space.w_ValueError,
                             space.wrap("byte must be in range(0, 256)"))
    for c in w_bytearray.data:
        if ord(c) == char:
            return space.w_True
    return space.w_False

def buffer__Bytearray(space, self):
    b = BytearrayBuffer(self.data)
    return space.wrap(b)

def ord__Bytearray(space, w_bytearray):
    if len(w_bytearray.data) != 1:
        raise OperationError(space.w_TypeError,
                             space.wrap("expected a character, but string"
                            "of length %s found" % len(w_bytearray.data)))
    return space.wrap(ord(w_bytearray.data[0]))


def gt__Bytearray_Bytearray(space, w_bytearray1, w_bytearray2):
    data1 = w_bytearray1.data
    data2 = w_bytearray2.data
    ncmp = min(len(data1), len(data2))
    # Search for the first index where items are different
    for p in range(ncmp):
        if data1[p] != data2[p]:
            return space.newbool(data1[p] > data2[p])
    # No more items to compare -- compare sizes
    return space.newbool(len(data1) > len(data2))

def ne__Bytearray_String(space, w_bytearray, w_other):
    return space.ne(str__Bytearray(space, w_bytearray), w_other)


### THESE MULTIMETHODS WORK BY PRETENDING TO BE A STRING, WTF

def String2Bytearray(space, w_str):
    data = [c for c in space.str_w(w_str)]
    return W_BytearrayObject(data)

def _convert_idx_params(space, w_self, w_start, w_stop):
    start = slicetype.eval_slice_index(space, w_start)
    stop = slicetype.eval_slice_index(space, w_stop)
    length = len(w_self.data)
    if start < 0:
        start += length
        if start < 0:
            start = 0
    if stop < 0:
        stop += length
        if stop < 0:
            stop = 0
    return start, stop, length

def str_splitlines__Bytearray_ANY(space, w_bytearray, w_keepends):
    w_str = str__Bytearray(space, w_bytearray)
    w_result = stringobject.str_splitlines__String_ANY(space, w_str, w_keepends)
    return space.newlist([
        new_bytearray(space, space.w_bytearray, makebytearraydata_w(space, w_entry))
        for w_entry in space.unpackiterable(w_result)
    ])

def str_translate__Bytearray_ANY_ANY(space, w_bytearray1, w_table, w_deletechars):
    # XXX slow, copies *twice* needs proper implementation
    w_str_copy = str__Bytearray(space, w_bytearray1)
    w_res = stringobject.str_translate__String_ANY_ANY(space, w_str_copy,
                                                       w_table, w_deletechars)
    return String2Bytearray(space, w_res)

def str_islower__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_islower__String(space, w_str)

def str_isupper__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isupper__String(space, w_str)

def str_isalpha__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isalpha__String(space, w_str)

def str_isalnum__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isalnum__String(space, w_str)

def str_isdigit__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isdigit__String(space, w_str)

def str_isspace__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_isspace__String(space, w_str)

def str_istitle__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_istitle__String(space, w_str)

def str_count__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_count__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_count__Bytearray_Int_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    char = w_char.intval
    start, stop, length = _convert_idx_params(space, w_bytearray, w_start, w_stop)
    count = 0
    for i in range(start, min(stop, length)):
        c = w_bytearray.data[i]
        if ord(c) == char:
            count += 1
    return space.wrap(count)

def str_index__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_index__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_rindex__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_rindex__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_find__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_find__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)

def str_rfind__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_char, w_start, w_stop):
    w_char = space.wrap(space.bufferstr_new_w(w_char))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_rfind__String_String_ANY_ANY(space, w_str, w_char,
                                                         w_start, w_stop)
def str_startswith__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_prefix, w_start, w_stop):
    w_prefix = space.wrap(space.bufferstr_new_w(w_prefix))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_startswith__String_String_ANY_ANY(space, w_str, w_prefix,
                                                              w_start, w_stop)

def str_startswith__Bytearray_Tuple_ANY_ANY(space, w_bytearray, w_prefix, w_start, w_stop):
    w_str = str__Bytearray(space, w_bytearray)
    w_prefix = space.newtuple([space.wrap(space.bufferstr_new_w(w_entry)) for w_entry in
                               space.unpackiterable(w_prefix)])
    return stringobject.str_startswith__String_Tuple_ANY_ANY(space, w_str, w_prefix,
                                                              w_start, w_stop)

def str_endswith__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_suffix, w_start, w_stop):
    w_suffix = space.wrap(space.bufferstr_new_w(w_suffix))
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_endswith__String_String_ANY_ANY(space, w_str, w_suffix,
                                                              w_start, w_stop)

def str_endswith__Bytearray_Tuple_ANY_ANY(space, w_bytearray, w_suffix, w_start, w_stop):
    w_str = str__Bytearray(space, w_bytearray)
    w_suffix = space.newtuple([space.wrap(space.bufferstr_new_w(w_entry)) for w_entry in
                               space.unpackiterable(w_suffix)])
    return stringobject.str_endswith__String_Tuple_ANY_ANY(space, w_str, w_suffix,
                                                              w_start, w_stop)

def str_replace__Bytearray_ANY_ANY_ANY(space, w_bytearray, w_str1, w_str2, w_max):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_replace__String_ANY_ANY_ANY(space, w_str, w_str1,
                                                         w_str2, w_max)
    return String2Bytearray(space, w_res)

def str_upper__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_upper__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_lower__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_lower__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_title__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_title__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_swapcase__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_swapcase__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_capitalize__Bytearray(space, w_bytearray):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_capitalize__String(space, w_str)
    return String2Bytearray(space, w_res)

def str_ljust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_ljust__String_ANY_ANY(space, w_str, w_width,
                                                   w_fillchar)
    return String2Bytearray(space, w_res)

def str_rjust__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_rjust__String_ANY_ANY(space, w_str, w_width,
                                                   w_fillchar)
    return String2Bytearray(space, w_res)

def str_center__Bytearray_ANY_ANY(space, w_bytearray, w_width, w_fillchar):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_center__String_ANY_ANY(space, w_str, w_width,
                                                    w_fillchar)
    return String2Bytearray(space, w_res)

def str_zfill__Bytearray_ANY(space, w_bytearray, w_width):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_zfill__String_ANY(space, w_str, w_width)
    return String2Bytearray(space, w_res)

def str_expandtabs__Bytearray_ANY(space, w_bytearray, w_tabsize):
    w_str = str__Bytearray(space, w_bytearray)
    w_res = stringobject.str_expandtabs__String_ANY(space, w_str, w_tabsize)
    return String2Bytearray(space, w_res)

def str_join__Bytearray_ANY(space, w_self, w_list):
    list_w = space.listview(w_list)
    if not list_w:
        return W_BytearrayObject([])
    data = w_self.data
    newdata = []
    for i in range(len(list_w)):
        w_s = list_w[i]
        if not (space.is_true(space.isinstance(w_s, space.w_str)) or
                space.is_true(space.isinstance(w_s, space.w_bytearray))):
            raise operationerrfmt(
                space.w_TypeError,
                "sequence item %d: expected string, %s "
                "found", i, space.type(w_s).getname(space))

        if data and i != 0:
            newdata.extend(data)
        newdata.extend([c for c in space.bufferstr_new_w(w_s)])
    return W_BytearrayObject(newdata)

def str_split__Bytearray_ANY_ANY(space, w_bytearray, w_by, w_maxsplit=-1):
    w_str = str__Bytearray(space, w_bytearray)
    if not space.is_w(w_by, space.w_None):
        w_by = space.wrap(space.bufferstr_new_w(w_by))
    w_list = space.call_method(w_str, "split", w_by, w_maxsplit)
    length = space.int_w(space.len(w_list))
    for i in range(length):
        w_i = space.wrap(i)
        space.setitem(w_list, w_i, String2Bytearray(space, space.getitem(w_list, w_i)))
    return w_list

def str_rsplit__Bytearray_ANY_ANY(space, w_bytearray, w_by, w_maxsplit=-1):
    w_str = str__Bytearray(space, w_bytearray)
    if not space.is_w(w_by, space.w_None):
        w_by = space.wrap(space.bufferstr_new_w(w_by))
    w_list = space.call_method(w_str, "rsplit", w_by, w_maxsplit)
    length = space.int_w(space.len(w_list))
    for i in range(length):
        w_i = space.wrap(i)
        space.setitem(w_list, w_i, String2Bytearray(space, space.getitem(w_list, w_i)))
    return w_list

def str_partition__Bytearray_ANY(space, w_bytearray, w_sub):
    w_str = str__Bytearray(space, w_bytearray)
    w_sub = space.wrap(space.bufferstr_new_w(w_sub))
    w_tuple = stringobject.str_partition__String_String(space, w_str, w_sub)
    w_a, w_b, w_c = space.fixedview(w_tuple, 3)
    return space.newtuple([
        String2Bytearray(space, w_a),
        String2Bytearray(space, w_b),
        String2Bytearray(space, w_c)])

def str_rpartition__Bytearray_ANY(space, w_bytearray, w_sub):
    w_str = str__Bytearray(space, w_bytearray)
    w_sub = space.wrap(space.bufferstr_new_w(w_sub))
    w_tuple = stringobject.str_rpartition__String_String(space, w_str, w_sub)
    w_a, w_b, w_c = space.fixedview(w_tuple, 3)
    return space.newtuple([
        String2Bytearray(space, w_a),
        String2Bytearray(space, w_b),
        String2Bytearray(space, w_c)])

def str_decode__Bytearray_ANY_ANY(space, w_bytearray, w_encoding, w_errors):
    w_str = str__Bytearray(space, w_bytearray)
    return stringobject.str_decode__String_ANY_ANY(space, w_str, w_encoding, w_errors)



# ____________________________________________________________

W_BytearrayObject.typedef = StdTypeDef("bytearray",
    __doc__ = '''bytearray() -> an empty bytearray
bytearray(sequence) -> bytearray initialized from sequence\'s items

If the argument is a bytearray, the return value is the same object.''',

    __new__ = gateway.interp2app(W_BytearrayObject.descr__new__.im_func),
    fromhex = gateway.interp2app(descr_fromhex, as_classmethod=True),

    __reduce__ = gateway.interp2app(W_BytearrayObject.descr__reduce__),
    __hash__ = None,

    append = gateway.interp2app(W_BytearrayObject.descr_append),
    extend = gateway.interp2app(W_BytearrayObject.descr_extend),
    insert = gateway.interp2app(W_BytearrayObject.descr_insert),
    pop = gateway.interp2app(W_BytearrayObject.descr_pop),
    remove = gateway.interp2app(W_BytearrayObject.descr_remove),
    reverse = gateway.interp2app(W_BytearrayObject.descr_reverse),

    strip = gateway.interp2app(W_BytearrayObject.descr_strip),
    lstrip = gateway.interp2app(W_BytearrayObject.descr_lstrip),
    rstrip = gateway.interp2app(W_BytearrayObject.descr_rstrip),
)

W_BytearrayObject.typedef.registermethods(globals())
register_all(vars(), sys.modules[__name__])