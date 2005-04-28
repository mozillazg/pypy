from pypy.objspace.std.objspace import *
from pypy.objspace.std.fake import wrap_exception
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std import slicetype
from pypy.objspace.std.strutil import string_to_int, string_to_long, ParseStringError
from pypy.tool.rarithmetic import intmask
from pypy.module.unicodedata import unicodedb

class W_UnicodeObject(W_Object):
    from pypy.objspace.std.unicodetype import unicode_typedef as typedef

    def __init__(w_self, space, unicodechars):
        W_Object.__init__(w_self, space)
        w_self._value = unicodechars
        if len(unicodechars) == 0:
            w_self.w_hash = space.wrap(0)
        else:
            w_self.w_hash = None
    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._value)

registerimplementation(W_UnicodeObject)

# Helper for converting int/long
import unicodedata
def unicode_to_decimal_w(space, w_unistr):
    unistr = w_unistr._value
    result = ['\0'] * len(unistr)
    digits = [ '0', '1', '2', '3', '4',
               '5', '6', '7', '8', '9']
    for i in xrange(len(unistr)):
        uchr = unistr[i]
        if _isspace(uchr):
            result[i] = ' '
            continue
        try:
            result[i] = digits[unicodedata.decimal(uchr)]
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
    return space.wrap(repr(u''.join(w_uni._value)))

def str__Unicode(space, w_uni):
    return space.call_method(w_uni, 'encode')

def cmp__Unicode_Unicode(space, w_left, w_right):
    left = w_left._value
    right = w_right._value
    for i in range(min(len(left), len(right))):
        test = ord(left[i]) - ord(right[i])
        if test < 0:
            return space.wrap(-1)
        if test > 0:
            return space.wrap(1)
            
    test = len(left) - len(right)
    if test < 0:
        return space.wrap(-1)
    if test > 0:
        return space.wrap(1)
    return space.wrap(0)
    
def ord__Unicode(space, w_uni):
    if len(w_uni._value) != 1:
        raise OperationError(space.w_TypeError, space.wrap('ord() expected a character'))
    return space.wrap(ord(w_uni._value[0]))

def add__Unicode_Unicode(space, w_left, w_right):
    left = w_left._value
    right = w_right._value
    leftlen = len(left)
    rightlen = len(right)
    result = [u'\0'] * (leftlen + rightlen)
    for i in range(leftlen):
        result[i] = left[i]
    for i in range(rightlen):
        result[i + leftlen] = right[i]
    return W_UnicodeObject(space, result)

def add__String_Unicode(space, w_left, w_right):
    return space.add(space.call_function(space.w_unicode, w_left) , w_right)

def add__Unicode_String(space, w_left, w_right):
    return space.add(w_left, space.call_function(space.w_unicode, w_right))

def contains__String_Unicode(space, w_container, w_item):
    return space.contains(space.call_function(space.w_unicode, w_container), w_item )

def contains__Unicode_Unicode(space, w_container, w_item):
    item = w_item._value
    container = w_container._value
    if len(item) == 0:
        return space.w_True
    for i in range(len(container) - len(item) + 1):
        for j in range(len(item)):
            if container[i + j]  != item[j]:
                break
        else:
            return space.w_True
    return space.w_False

def unicode_join__Unicode_ANY(space, w_self, w_list):
    list = space.unpackiterable(w_list)
    delim = w_self._value
    totlen = 0
    if len(list) == 0:
        return W_UnicodeObject(space, [])
    if len(list) == 1:
        return space.call_function(space.w_unicode, list[0])
    for i in range(len(list)):
        list[i] = space.call_function(space.w_unicode, list[i])._value
        totlen += len(list[i])
    totlen += len(delim) * (len(list) - 1)
    # Allocate result
    result = [u'\0'] * totlen
    first = list[0]
    for i in range(len(first)):
        result[i] = first[i]
    offset = len(first)
    for i in range(1, len(list)):
        item = list[i]
        # Add delimiter
        for j in range(len(delim)):
            result[offset + j] = delim[j]
        offset += len(delim)
        # Add item from list
        for j in range(len(item)):
            result[offset + j] = item[j]
        offset += len(item)
    return W_UnicodeObject(space, result)

def unicode_encode__Unicode_String_String(space, w_self, w_encoding, w_errors):
    try:
        return space.wrap(u''.join(w_self._value).encode(space.str_w(w_encoding), space.str_w(w_errors)))
    except:
        wrap_exception(space)
def unicode_encode__Unicode_String_None(space, w_self, w_encoding, w_none):
    try:
        return space.wrap(u''.join(w_self._value).encode(space.str_w(w_encoding)))
    except:
        wrap_exception(space)

def unicode_encode__Unicode_None_None(space, w_self, w_encoding, w_errors):
    try:
        return space.wrap(u''.join(w_self._value).encode())
    except:
        wrap_exception(space)

def hash__Unicode(space, w_uni):
    if w_uni.w_hash is None:
        chars = w_uni._value
        x = ord(chars[0]) << 7
        for c in chars:
            x = intmask((1000003 * x) ^ ord(c))
        h = intmask(x ^ len(chars))
        if h == -1:
            h = -2
        w_uni.w_hash = space.wrap(h)
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
    return W_UnicodeObject(space, [uni[ival]])

def getitem__Unicode_Slice(space, w_uni, w_slice):
    uni = w_uni._value
    length = len(uni)
    start, stop, step, sl = slicetype.indices4(space, w_slice, length)
    r = [uni[start + i*step] for i in range(sl)]
    return W_UnicodeObject(space, r)


def mul__Unicode_ANY(space, w_uni, w_times):
    chars = w_uni._value
    charlen = len(chars)
    times = space.int_w(w_times)
    if times <= 0 or charlen == 0:
        return W_UnicodeObject(space, [])
    if times == 1:
        return w_uni
    if charlen == 1:
        return W_UnicodeObject(space, [w_uni._value[0]] * times)

    result = [u'\0'] * (charlen * times)
    for i in range(times):
        offset = i * charlen
        for j in range(charlen):
            result[offset + j] = chars[j]
    return W_UnicodeObject(space, result)

def mul__ANY_Unicode(space, w_times, w_uni):
    return space.mul(w_uni, w_times)

def _isspace(uchar):
    code = ord(uchar)
    try:
        return unicodedb.category[code] == 'Zs' or unicodedb.bidirectional[code] in ("WS", "B", "S")
    except:
        return False

def _strip(space, w_self, w_chars, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    u_chars = w_chars._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        while lpos < rpos and u_self[lpos] in u_chars:
           lpos += 1
       
    if right:
        while rpos > lpos and u_self[rpos - 1] in u_chars:
           rpos -= 1
           
    result = [u'\0'] * (rpos - lpos)
    for i in range(rpos - lpos):
        result[i] = u_self[lpos + i]
    return W_UnicodeObject(space, result)

def _strip_none(space, w_self, left, right):
    "internal function called by str_xstrip methods"
    u_self = w_self._value
    
    lpos = 0
    rpos = len(u_self)
    
    if left:
        while lpos < rpos and _isspace(u_self[lpos]):
           lpos += 1
       
    if right:
        while rpos > lpos and _isspace(u_self[rpos - 1]):
           rpos -= 1
       
    result = [u'\0'] * (rpos - lpos)
    for i in range(rpos - lpos):
        result[i] = u_self[lpos + i]
    return W_UnicodeObject(space, result)

def unicode_strip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 1)
def unicode_strip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 1)
def unicode_strip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'strip',
                             space.call_function(space.w_unicode, w_chars))

def unicode_lstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 1, 0)
def unicode_lstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 0)
def unicode_lstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'lstrip',
                             space.call_function(space.w_unicode, w_chars))

def unicode_rstrip__Unicode_None(space, w_self, w_chars):
    return _strip_none(space, w_self, 0, 1)
def unicode_rstrip__Unicode_Unicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 0, 1)
def unicode_rstrip__Unicode_String(space, w_self, w_chars):
    return space.call_method(w_self, 'rstrip',
                             space.call_function(space.w_unicode, w_chars))

import unicodetype
register_all(vars(), unicodetype)

# str.strip(unicode) needs to convert self to unicode and call unicode.strip
# we use the following magic to register strip_string_unicode as a String multimethod.
class str_methods:
    import stringtype
    W_UnicodeObject = W_UnicodeObject
    from pypy.objspace.std.stringobject import W_StringObject
    def str_strip__String_Unicode(space, w_self, w_chars ):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'strip', w_chars)
    def str_lstrip__String_Unicode(space, w_self, w_chars ):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'lstrip', w_chars)
        self = w_self._value
    def str_rstrip__String_Unicode(space, w_self, w_chars ):
        return space.call_method(space.call_function(space.w_unicode, w_self),
                                 'rstrip', w_chars)

    register_all(vars(), stringtype)
