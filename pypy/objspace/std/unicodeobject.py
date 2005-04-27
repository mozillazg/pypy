from pypy.objspace.std.objspace import *
from pypy.objspace.std.fake import wrap_exception
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std import slicetype
from pypy.objspace.std.strutil import string_to_int, string_to_long, ParseStringError

class W_UnicodeObject(W_Object):
    from pypy.objspace.std.unicodetype import unicode_typedef as typedef

    def __init__(w_self, space, unicodechars):
        W_Object.__init__(w_self, space)
        w_self._value = unicodechars
        w_self.w_hash = None

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

    def unwrap(w_self): 
        return w_self._value # This is maybe not right

registerimplementation(W_UnicodeObject)

# Helper for converting int/long
import unicodedata
def unicode_to_decimal_w(space, w_unistr):
    unistr = space.unwrap(w_unistr)
    result = [' '] * len(unistr)
    for i in xrange(len(unistr)):
        uchr = unistr[i]
        if uchr.isspace():
            result[i] = ' '
            continue
        try:
            result[i] = chr(ord('0') + unicodedata.decimal(uchr))
            continue
        except ValueError:
            ch = ord(uchr)
            if 0 < ch < 256:
                result[i] = chr(ch)
                continue
        raise OperationError(space.w_UnicodeEncodeError, space.wrap('invalid decimal Unicode string'))
    return ''.join(result)

# string-to-unicode delegation
def delegate_String2Unicode(w_str):
    space = w_str.space
    return space.call_function(space.w_unicode, w_str)

def str_w__Unicode(space, w_uni):
    return space.str_w(space.str(w_uni))

def repr__Unicode(space, w_uni):
    return space.wrap(repr(w_uni._value))

def str__Unicode(space, w_uni):
    return space.call_method(w_uni, 'encode')

def cmp__Unicode_ANY(space, w_uni, w_other):
    try:
        return space.newbool(cmp(space.unwrap(w_uni), space.unwrap(w_other)))
    except:
        wrap_exception(space)
        
def ord__Unicode(space, w_uni):
    try:
        return space.wrap(ord(w_uni._value))
    except:
        wrap_exception(space)

def add__Unicode_Unicode(space, w_left, w_right):
    return space.wrap(space.unwrap(w_left) + space.unwrap(w_right))
def add__String_Unicode(space, w_left, w_right):
    return space.wrap(space.str_w(w_left) + space.unwrap(w_right))
def add__Unicode_String(space, w_left, w_right):
    return space.wrap(space.unwrap(w_left) + space.str_w(w_right))

def contains__String_Unicode(space, w_left, w_right):
    try:
        return space.wrap(space.unwrap(w_right) in space.unwrap(w_left))
    except:
        wrap_exception(space)

def contains__Unicode_Unicode(space, w_left, w_right):
    return space.wrap(space.unwrap(w_right) in space.unwrap(w_left))

def unicode_join__Unicode_ANY(space, w_self, w_list):
    list = space.unpackiterable(w_list)
    self = w_self._value
    for i in range(len(list)):
        list[i] = space.unwrap(space.call_function(space.w_unicode, list[i]))
    return space.wrap(self.join(list))

def unicode_encode__Unicode_String_String(space, w_self, w_encoding, w_errors):
    try:
        return space.wrap(w_self._value.encode(space.str_w(w_encoding), space.str_w(w_errors)))
    except:
        wrap_exception(space)
def unicode_encode__Unicode_String_None(space, w_self, w_encoding, w_none):
    try:
        return space.wrap(w_self._value.encode(space.str_w(w_encoding)))
    except:
        wrap_exception(space)

def unicode_encode__Unicode_None_None(space, w_self, w_encoding, w_errors):
    try:
        return space.wrap(w_self._value.encode())
    except:
        wrap_exception(space)

def hash__Unicode(space, w_uni):
    if w_uni.w_hash is None:
        w_uni.w_hash = space.wrap(hash(w_uni._value))
    return w_uni.w_hash

def len__Unicode(space, w_uni):
    return space.wrap(len(w_uni._value))

def getitem__Unicode_ANY(space, w_uni, w_index):
    ival = space.int_w(w_index)
    uni = w_uni._value
    ulen = len(uni)
    if ival < 0:
        ival += ulen
    if ival < 0 or ival >= ulen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("unicode index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return W_UnicodeObject(space, uni[ival])

def getitem__Unicode_Slice(space, w_uni, w_slice):
    uni = w_uni._value
    length = len(uni)
    start, stop, step, sl = slicetype.indices4(space, w_slice, length)
    if step == 1:
        return space.wrap(uni[start:stop])
    r = [uni[start + i*step] for i in range(sl)]
    return space.wrap(u''.join(r))

def mul__Unicode_ANY(space, w_uni, w_times):
    return space.wrap(w_uni._value * space.int_w(w_times))

def mul__ANY_Unicode(space, w_times, w_uni):
    return space.wrap(w_uni._value * space.int_w(w_times))

def unicode_strip__Unicode_None(space, w_self, w_chars):
    return space.wrap(w_self._value.strip())
def unicode_strip__Unicode_String(space, w_self, w_chars):
    return space.wrap(w_self._value.strip(space.str_w(w_chars)))
def unicode_strip__Unicode_Unicode(space, w_self, w_chars):
    return space.wrap(w_self._value.strip(w_chars._value))

def unicode_lstrip__Unicode_None(space, w_self, w_chars):
    return space.wrap(w_self._value.lstrip())
def unicode_lstrip__Unicode_String(space, w_self, w_chars):
    return space.wrap(w_self._value.lstrip(space.str_w(w_chars)))
def unicode_lstrip__Unicode_Unicode(space, w_self, w_chars):
    return space.wrap(w_self._value.lstrip(w_chars._value))

def unicode_rstrip__Unicode_None(space, w_self, w_chars):
    return space.wrap(w_self._value.rstrip())
def unicode_rstrip__Unicode_String(space, w_self, w_chars):
    return space.wrap(w_self._value.rstrip(space.str_w(w_chars)))
def unicode_rstrip__Unicode_Unicode(space, w_self, w_chars):
    return space.wrap(w_self._value.rstrip(w_chars._value))

import unicodetype
register_all(vars(), unicodetype)

# str.strip(unicode) needs to convert self to unicode and call unicode.strip
# we use the following magic to register strip_string_unicode as a String multimethod.
class str_methods:
    import stringtype
    W_UnicodeObject = W_UnicodeObject
    from pypy.objspace.std.stringobject import W_StringObject
    def str_strip__String_Unicode(space, w_self, w_chars ):
        self = w_self._value
        return space.wrap( unicode(self).strip( space.unwrap(w_chars) ) )
    def str_lstrip__String_Unicode(space, w_self, w_chars ):
        self = w_self._value
        return space.wrap( unicode(self).lstrip( space.unwrap(w_chars) ) )
    def str_rstrip__String_Unicode(space, w_self, w_chars ):
        self = w_self._value
        return space.wrap( unicode(self).rstrip( space.unwrap(w_chars) ) )
    register_all(vars(), stringtype)
