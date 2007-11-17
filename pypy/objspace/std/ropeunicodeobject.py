from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.unicodeobject import _normalize_index
from pypy.objspace.std.ropeobject import W_RopeObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std import rope
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std import slicetype
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.rlib.rarithmetic import intmask, ovfcheck
from pypy.module.unicodedata import unicodedb_3_2_0 as unicodedb
from pypy.tool.sourcetools import func_with_new_name

from pypy.objspace.std.formatting import mod_format


def wrapunicode(space, uni):
    return W_RopeUnicodeObject(rope.rope_from_unicode(uni))

def unicode_from_string(space, w_str):
    from pypy.objspace.std.unicodetype import getdefaultencoding, \
        unicode_from_encoded_object
    assert isinstance(w_str, W_RopeObject)
    node = w_str._node
    encoding = getdefaultencoding(space)
    if encoding == 'ascii':
        result = rope.str_decode_ascii(node)
        if result is not None:
            return W_RopeUnicodeObject(result)
    elif encoding == 'latin-1':
        assert node.is_bytestring()
        return W_RopeUnicodeObject(node)
    elif encoding == "utf-8":
        result = rope.str_decode_utf8(node)
        if result is not None:
            return W_RopeUnicodeObject(result)
    return unicode_from_encoded_object(space, w_str, encoding, "strict")


class W_RopeUnicodeObject(W_Object):
    from pypy.objspace.std.unicodetype import unicode_typedef as typedef

    def __init__(w_self, node):
        w_self._node = node

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._node)

    def unwrap(w_self, space):
        # for testing
        return w_self._node.flatten_unicode()

    def create_if_subclassed(w_self):
        if type(w_self) is W_RopeUnicodeObject:
            return w_self
        return W_RopeUnicodeObject(w_self._value)

W_RopeUnicodeObject.EMPTY = W_RopeUnicodeObject(rope.LiteralStringNode.EMPTY)

registerimplementation(W_RopeUnicodeObject)


def ropeunicode_w(space, w_str):
    if isinstance(w_str, W_RopeUnicodeObject):
        return w_str._node
    # XXX do the right thing for W_RopeObject
    return rope.LiteralUnicodeNode(space.unicode_w(w_str))


# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_RopeUnicodeObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected unicode"))
    unistr = w_unistr._node
    length = unistr.length()
    result = ['\0'] * length
    digits = [ '0', '1', '2', '3', '4',
               '5', '6', '7', '8', '9']
    iter = rope.ItemIterator(unistr)
    for i in range(length):
        uchr = iter.nextint()
        if unicodedb.isspace(uchr):
            result[i] = ' '
            continue
        try:
            result[i] = digits[unicodedb.decimal(uchr)]
        except KeyError:
            if 0 < uchr < 256:
                result[i] = chr(uchr)
            else:
                w_encoding = space.wrap('decimal')
                w_start = space.wrap(i)
                w_end = space.wrap(i+1)
                w_reason = space.wrap('invalid decimal Unicode string')
                raise OperationError(space.w_UnicodeEncodeError,space.newtuple ([w_encoding, w_unistr, w_start, w_end, w_reason]))
    return ''.join(result)

# string-to-unicode delegation
def delegate_Rope2RopeUnicode(space, w_rope):
    w_uni = unicode_from_string(space, w_rope)
    assert isinstance(w_uni, W_RopeUnicodeObject) # help the annotator!
    return w_uni

def str_w__RopeUnicode(space, w_uni):
    return space.str_w(space.str(w_uni))

def unicode_w__RopeUnicode(space, w_uni):
    return w_uni._node.flatten_unicode()

def str__RopeUnicode(space, w_uni):
    return space.call_method(w_uni, 'encode')

def lt__RopeUnicode_RopeUnicode(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) < 0)

def le__RopeUnicode_RopeUnicode(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) <= 0)

def _eq(w_str1, w_str2):
    result = rope.eq(w_str1._node, w_str2._node)
    return result

def eq__RopeUnicode_RopeUnicode(space, w_str1, w_str2):
    return space.newbool(_eq(w_str1, w_str2))

def ne__RopeUnicode_RopeUnicode(space, w_str1, w_str2):
    return space.newbool(not _eq(w_str1, w_str2))

def gt__RopeUnicode_RopeUnicode(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) > 0)

def ge__RopeUnicode_RopeUnicode(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) >= 0)


def ord__RopeUnicode(space, w_uni):
    if w_uni.length() != 1:
        raise OperationError(space.w_TypeError, space.wrap('ord() expected a character'))
    return space.wrap(w_uni._node.getint(0))

def getnewargs__RopeUnicode(space, w_uni):
    return space.newtuple([W_RopeUnicodeObject(w_uni._node)])

def add__RopeUnicode_RopeUnicode(space, w_left, w_right):
    right = w_right._node
    left = w_left._node
    try:
        return W_RopeUnicodeObject(rope.concatenate(left, right))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))

def add__Rope_RopeUnicode(space, w_left, w_right):
    return space.add(unicode_from_string(space, w_left) , w_right)

def add__RopeUnicode_Rope(space, w_left, w_right):
    return space.add(w_left, unicode_from_string(space, w_right))

def contains__RopeUnicode_RopeUnicode(space, w_container, w_item):
    item = w_item._node
    container = w_container._node
    return space.newbool(rope.find(container, item) != -1)

def contains__Rope_RopeUnicode(space, w_container, w_item):
    return space.contains(unicode_from_string(space, w_container), w_item )

def unicode_join__RopeUnicode_ANY(space, w_self, w_list):
    l_w = space.unpackiterable(w_list)
    delim = w_self._value
    totlen = 0
    if len(l_w) == 0:
        return W_RopeUnicodeObject.EMPTY
    if (len(l_w) == 1 and
        space.is_w(space.type(l_w[0]), space.w_unicode)):
        return l_w[0]
    
    values_list = []
    for i in range(len(l_w)):
        w_item = l_w[i]
        if isinstance(w_item, W_RopeUnicodeObject):
            # shortcut for performane
            item = w_item._node
        elif space.is_true(space.isinstance(w_item, space.w_str)):
            item = unicode_from_string(space, w_item)._node
        else:
            w_msg = space.mod(space.wrap('sequence item %d: expected string or Unicode'),
                              space.wrap(i))
            raise OperationError(space.w_TypeError, w_msg)
        values_list.append(item)
    try:
        return W_RopeUnicodeObject(rope.join(self, values_list))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))

def hash__RopeUnicode(space, w_uni):
    return space.wrap(rope.hash_rope(w_uni._node))

def len__RopeUnicode(space, w_uni):
    return space.wrap(w_uni._node.length())

def getitem__RopeUnicode_ANY(space, w_uni, w_index):
    ival = space.getindex_w(w_index, space.w_IndexError, "string index")
    uni = w_uni._node
    ulen = uni.length()
    if ival < 0:
        ival += ulen
    if ival < 0 or ival >= ulen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("unicode index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return W_RopeUnicodeObject(uni.getrope(ival))

def getitem__RopeUnicode_Slice(space, w_uni, w_slice):
    node = w_uni._noed
    length = node.length()
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        return W_RopeUnicodeObject.EMPTY
    return W_RopeUnicodeObject(rope.getslice(node, start, stop, step, sl))

def mul__RopeUnicode_ANY(space, w_uni, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    node = w_uni._node
    try:
        return W_RopeUnicodeObject(rope.multiply(node, mul))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))

def mul__ANY_RopeUnicode(space, w_times, w_uni):
    return mul__RopeUnicode_ANY(space, w_uni, w_times)


def make_generic(funcname):
    def func(space, w_self): 
        node = w_self._node
        if node.length() == 0:
            return space.w_False
        iter = rope.ItemIterator(node)
        for idx in range(node.length()):
            if not getattr(unicodedb, funcname)(iter.nextint()):
                return space.w_False
        return space.w_True
    return func_with_new_name(func, "unicode_%s__RopeUnicode" % (funcname, ))

unicode_isspace__RopeUnicode = make_generic("isspace")
unicode_isalpha__RopeUnicode = make_generic("isalpha")
unicode_isalnum__RopeUnicode = make_generic("isalnum")
unicode_isdecimal__RopeUnicode = make_generic("isdecimal")
unicode_isdigit__RopeUnicode = make_generic("isdigit")
unicode_isnumeric__RopeUnicode = make_generic("isnumeric")

def unicode_islower__RopeUnicode(space, w_unicode):
    cased = False
    iter = rope.ItemIterator(w_unicode._node)
    while 1:
        try:
            ch = iter.nextint()
        except StopIteration:
            return space.newbool(cased)
        if (unicodedb.isupper(ch) or
            unicodedb.istitle(ch)):
            return space.w_False
        if not cased and unicodedb.islower(ch):
            cased = True

def unicode_isupper__RopeUnicode(space, w_unicode):
    cased = False
    iter = rope.ItemIterator(w_unicode._node)
    while 1:
        try:
            ch = iter.nextint()
        except StopIteration:
            return space.newbool(cased)
        if (unicodedb.islower(ch) or
            unicodedb.istitle(ch)):
            return space.w_False
        if not cased and unicodedb.isupper(ch):
            cased = True

def unicode_istitle__RopeUnicode(space, w_unicode):
    cased = False
    previous_is_cased = False
    iter = rope.ItemIterator(w_unicode._node)
    while 1:
        try:
            ch = iter.nextint()
        except StopIteration:
            return space.newbool(cased)
        if (unicodedb.isupper(ch) or
            unicodedb.istitle(ch)):
            if previous_is_cased:
                return space.w_False
            previous_is_cased = cased = True
        elif unicodedb.islower(ch):
            if not previous_is_cased:
                return space.w_False
            previous_is_cased = cased = True
        else:
            previous_is_cased = False


def _strip(space, w_self, w_chars, left, right):
    "internal function called by str_xstrip methods"
    XXX
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
           
    assert rpos >= 0
    result = u_self[lpos: rpos]
    return W_UnicodeObject(result)

def unicode_strip__RopeUnicode_None(space, w_self, w_chars):
    return W_RopeUnicodeObject(rope.strip(w_self._none, True, True, _isspace))
def unicode_strip__RopeUnicode_RopeUnicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 1)
def unicode_strip__RopeUnicode_Rope(space, w_self, w_chars):
    return space.call_method(w_self, 'strip',
                             unicode_from_string(space, w_chars))

def unicode_lstrip__RopeUnicode_None(space, w_self, w_chars):
    return W_RopeUnicodeObject(rope.strip(w_self._none, True, False, _isspace))
def unicode_lstrip__RopeUnicode_RopeUnicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 1, 0)
def unicode_lstrip__RopeUnicode_Rope(space, w_self, w_chars):
    return space.call_method(w_self, 'lstrip',
                             unicode_from_string(space, w_chars))

def unicode_rstrip__RopeUnicode_None(space, w_self, w_chars):
    return W_RopeUnicodeObject(rope.strip(w_self._none, False, True, _isspace))
def unicode_rstrip__RopeUnicode_RopeUnicode(space, w_self, w_chars):
    return _strip(space, w_self, w_chars, 0, 1)
def unicode_rstrip__RopeUnicode_Rope(space, w_self, w_chars):
    return space.call_method(w_self, 'rstrip',
                             unicode_from_string(space, w_chars))

def unicode_capitalize__RopeUnicode(space, w_self):
    input = w_self._node
    length = input.length()
    if length == 0:
        return w_self
    result = [u'\0'] * length
    iter = rope.ItemIterator(input)
    result[0] = unichr(unicodedb.toupper(iter.nextint()))
    for i in range(1, length):
        result[i] = unichr(unicodedb.tolower(iter.nextint()))
    return W_RopeUnicodeObject(rope.rope_from_unicharlist(result))

def unicode_title__RopeUnicode(space, w_self):
    input = w_self._node
    length = input.length()
    if length == 0:
        return w_self
    result = [u'\0'] * length
    iter = rope.ItemIterator(input)

    previous_is_cased = False
    for i in range(len(input)):
        unichar = iter.nextint()
        if previous_is_cased:
            result[i] = unichr(unicodedb.tolower(unichar))
        else:
            result[i] = unichr(unicodedb.totitle(unichar))
        previous_is_cased = unicodedb.iscased(unichar)
    return W_RopeUnicodeObject(rope.rope_from_unicharlist(result))


def _local_transform(node, transform):
    l = node.length()
    res = [u' '] * l
    iter = rope.ItemIterator(node)
    for i in range(l):
        ch = iter.nextint()
        res[i] = transform(ch)

    return W_RopeUnicodeObject(rope.rope_from_unicharlist(res))
_local_transform._annspecialcase_ = "specialize:arg(1)"

def _tolower(ordch):
    return unichr(unicodedb.tolower(ordch))
def unicode_lower__RopeUnicode(space, w_self):
    return _local_transform(w_self._node, _tolower)

def _toupper(ordch):
    return unichr(unicodedb.toupper(ordch))
def unicode_upper__RopeUnicode(space, w_self):
    return _local_transform(w_self._node, _toupper)

def _swapcase(ordch):
    if unicodedb.islower(unichar):
        return unichr(unicodedb.toupper(unichar))
    elif unicodedb.isupper(unichar):
        return unichr(unicodedb.tolower(unichar))
    else:
        return unichr(ordch)

def unicode_swapcase__RopeUnicode(space, w_self):
    return _local_transform(w_self._node, _swapcase)

def _convert_idx_params(space, w_self, w_start, w_end):
    self = w_self._node
    length = w_self._node.length()
    start = slicetype.adapt_bound(space, length, w_start)
    end = slicetype.adapt_bound(space, length, w_end)

    assert start >= 0
    assert end >= 0

    return (self, start, end)

def _check_startswith_substring(str, substr, start, end):
    XXX
    substr_len = len(substr)
    
    if end - start < substr_len:
        return False # substring is too long
    
    for i in range(substr_len):
        if str[start + i] != substr[i]:
            return False
    return True    

def _check_endswith_substring(str, substr, start, end):
    XXX
    substr_len = len(substr)

    if end - start < substr_len:
        return False # substring is too long
    start = end - substr_len
    for i in range(substr_len):
        if str[start + i] != substr[i]:
            return False
    return True

def unicode_endswith__RopeUnicode_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    return space.newbool(rope.endswith(self, w_substr._node, start, end))

def unicode_startswith__RopeUnicode_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    # XXX this stuff can be waaay better for ootypebased backends if
    #     we re-use more of our rpython machinery (ie implement startswith
    #     with additional parameters as rpython)

    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    return space.newbool(rope.startswith(self, w_substr._node, start, end))

def unicode_startswith__RopeUnicode_Tuple_ANY_ANY(space, w_unistr, w_prefixes,
                                              w_start, w_end):
    unistr, start, end = _convert_idx_params(space, w_unistr, w_start, w_end)
    for w_prefix in space.unpacktuple(w_prefixes):
        prefix = unicoderope_w(space, w_prefix)
        if rope.startswith(self, prefxix, start, end)
            return space.w_True
    return space.w_False

def unicode_endswith__RopeUnicode_Tuple_ANY_ANY(space, w_unistr, w_suffixes,
                                            w_start, w_end):
    unistr, start, end = _convert_idx_params(space, w_unistr, w_start, w_end)
    for w_suffix in space.unpacktuple(w_suffixes):
        suffix = unicoderope_w(space, w_suffix)
        if _check_endswith_substring(unistr, suffix, start, end):
            return space.w_True
    return space.w_False


def _to_unichar_w(space, w_char):
    try:
        unistr = ropeunicode_w(space, w_char)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            msg = 'The fill character cannot be converted to Unicode'
            raise OperationError(space.w_TypeError, space.wrap(msg))
        else:
            raise

    if unistr.length() != 1:
        raise OperationError(space.w_TypeError, space.wrap('The fill character must be exactly one character long'))
    return unistr

def unicode_center__RopeUnicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._node
    length = self.length
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - length
    if padding < 0:
        return w_self.create_if_subclassed()
    offset = padding // 2
    pre = rope.multiply(fillchar, offset)
    post = rope.multiply(fillchar, (padding - offset))
    centered = rope.rebalance([pre, node, post])
    return W_RopeUnicodeObject(centered)

def unicode_ljust__RopeUnicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._node
    length = self.length
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - length
    if padding < 0:
        return w_self.create_if_subclassed()
    resultnode = rope.concatenate(self, rope.multiply(fillchar, d))
    return W_RopeUnicodeObject(resultnode)

def unicode_rjust__RopeUnicode_ANY_ANY(space, w_self, w_width, w_fillchar):
    self = w_self._node
    length = self.length
    width = space.int_w(w_width)
    fillchar = _to_unichar_w(space, w_fillchar)
    padding = width - length
    if padding < 0:
        return w_self.create_if_subclassed()
    resultnode = rope.concatenate(rope.multiply(fillchar, d), self)
    return W_RopeUnicodeObject(resultnode)
    
def unicode_zfill__RopeUnicode_ANY(space, w_self, w_width):
    self = w_self._value
    length = self.length
    width = space.int_w(w_width)
    if self.length() == 0:
        return W_RopeUnicodeObject(
            rope.multiply(rope.LiteralStringNode.PREBUILT[ord(" ")], width))
    padding = width - self.length()
    if padding <= 0:
        return w_self.create_if_subclassed()
    firstchar = self.getunichar(0)
    if firstchar in (u'+', u'-'):
        return W_RopeUnicodeObject(rope.rebalance(
            [rope.LiteralStringNode.PREBUILT[ord(firstchar)],
             rope.multiply(zero, middle),
             rope.getslice_one(node, 1, length)]))
    else:
        middle = width - length
        return W_RopeUnicodeObject(rope.concatenate(
            rope.multiply(zero, middle), node))

def unicode_splitlines__RopeUnicode_ANY(space, w_self, w_keepends):
    XXX
    self = w_self._value
    keepends = 0
    if space.int_w(w_keepends):
        keepends = 1
    if len(self) == 0:
        return space.newlist([])
    
    start = 0
    end = len(self)
    pos = 0
    lines = []
    while pos < end:
        if unicodedb.islinebreak(ord(self[pos])):
            if (self[pos] == u'\r' and pos + 1 < end and
                self[pos + 1] == u'\n'):
                # Count CRLF as one linebreak
                lines.append(W_UnicodeObject(self[start:pos + keepends * 2]))
                pos += 1
            else:
                lines.append(W_UnicodeObject(self[start:pos + keepends]))
            pos += 1
            start = pos
        else:
            pos += 1
    if not unicodedb.islinebreak(ord(self[end - 1])):
        lines.append(W_UnicodeObject(self[start:]))
    return space.newlist(lines)


def unicode_find__RopeUnicode_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    sub = w_substr._node
    return space.wrap(rope.find(self, sub, start, end))

def unicode_rfind__RopeUnicode_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    self = self.flatten_unicode()
    sub = sub.flatten_unicode()
    res = self.rfind(sub, start, end)
    return wrapint(space, res)

def unicode_index__RopeUnicode_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    sub = w_substr._node
    res = rope.find(self, sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))
    return space.wrap(res)

def unicode_rindex__RopeUnicode_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    # XXX works but flattens string
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    self = self.flatten_unicode()
    sub = sub.flatten_unicode()
    res = self.rfind(sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return wrapint(space, res)

def unicode_count__RopeUnicode_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
    self, start, end = _convert_idx_params(space, w_self, w_start, w_end)
    substr = w_substr._value
    return space.wrap(self.count(substr, start, end))

def unicode_split__RopeUnicode_None_ANY(space, w_self, w_none, w_maxsplit):
    self = w_self._value
    maxsplit = space.int_w(w_maxsplit)
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    inword = 0

    while maxsplit != 0 and start < end:
        index = start
        for index in range(start, end):
            if _isspace(self[index]):
                break
            else:
                inword = 1
        else:
            break
        if inword == 1:
            parts.append(W_UnicodeObject(self[start:index]))
            maxsplit -= 1
        # Eat whitespace
        for start in range(index + 1, end):
            if not _isspace(self[start]):
                break
        else:
            return space.newlist(parts)

    parts.append(W_UnicodeObject(self[start:]))
    return space.newlist(parts)

def unicode_split__RopeUnicode_RopeUnicode_ANY(space, w_self, w_delim, w_maxsplit):
    maxsplit = space.int_w(w_maxsplit)
    start = 0
    selfnode = w_self._node
    bynode = w_by._node
    bylen = bynode.length()
    if bylen == 0:
        raise OperationError(space.w_ValueError, space.wrap("empty separator"))
    res_w = [W_RopeUnicodeObject(node)
                for node in rope.split(selfnode, bynode, maxsplit)]
    return space.newlist(res_w)

def unicode_rsplit__RopeUnicode_None_ANY(space, w_self, w_none, w_maxsplit):
    XXX
    self = w_self._value
    maxsplit = space.int_w(w_maxsplit)
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    inword = 0

    while maxsplit != 0 and start < end:
        index = end
        for index in range(end-1, start-1, -1):
            if _isspace(self[index]):
                break
            else:
                inword = 1
        else:
            break
        if inword == 1:
            parts.append(W_UnicodeObject(self[index+1:end]))
            maxsplit -= 1
        # Eat whitespace
        for end in range(index, start-1, -1):
            if not _isspace(self[end-1]):
                break
        else:
            return space.newlist(parts)

    parts.append(W_UnicodeObject(self[:end]))
    parts.reverse()
    return space.newlist(parts)

def unicode_rsplit__RopeUnicode_RopeUnicode_ANY(space, w_self, w_delim, w_maxsplit):
    # XXX works but flattens
    self = w_self._node.flatten_unicode()
    delim = w_delim._node.flatten_unicode()
    maxsplit = space.int_w(w_maxsplit)
    delim_len = len(delim)
    if delim_len == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap('empty separator'))
    parts = []
    if len(self) == 0:
        return space.newlist([])
    start = 0
    end = len(self)
    while maxsplit != 0:
        index = self.rfind(delim, 0, end)
        if index < 0:
            break
        parts.append(W_RopeUnicodeObject(
            rope.getslice_one(w_self._node, index+delim_len, end)))
        end = index
        maxsplit -= 1
    parts.append(W_RopeUnicodeObject(
        rope.getslice_one(w_self._node, 0, :end)))
    parts.reverse()
    return space.newlist(parts)

def _split_into_chars(self, maxsplit):
    if maxsplit == 0:
        return [self]
    index = 0
    end = len(self)
    parts = [rope.LiteralStringNode.EMPTY]
    maxsplit -= 1
    while maxsplit != 0:
        if index >= end:
            break
        parts.append(self.getrope(index))
        index += 1
        maxsplit -= 1
    parts.append(rope.getslice_one(self, index, self.length())
    return parts

def unicode_replace__RopeUnicode_RopeUnicode_RopeUnicode_ANY(
        space, w_self, w_old, w_new, w_maxsplit):
    old = w_old._node
    oldlength = old.length
    if not oldlength:
        self = w_self._value
        maxsplit = space.int_w(w_maxsplit)
        parts = _split_into_chars(self, maxsplit)
        return W_RopeUnicodeObject(rope.join(w_new._node, parts))
    substrings = rope.split(node, old, maxsplit)
    if not substrings:
        return w_self.create_if_subclassed()
    substrings = rope.split(node, sub, maxsplit)
    if substrings is None:
        return w_self.create_if_subclassed()
    try:
        return W_RopeObject(rope.join(by, substrings))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))
    try:
        return W_RopeObject(rope.join(by, substrings))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))
    return W_UnicodeObject(w_new._value.join(parts))
    

def unicode_encode__Unicode_ANY_ANY(space, w_unistr,
                                    w_encoding=None,
                                    w_errors=None):

    from pypy.objspace.std.unicodetype import getdefaultencoding, \
        _get_encoding_and_errors, encode_object
    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    if encoding is None:
        encoding = getdefaultencoding(space)
    w_retval = encode_object(space, w_unistr, encoding, errors)
    return w_retval

def unicode_partition__Unicode_Unicode(space, w_unistr, w_unisub):
    self = w_unistr._node
    sub = w_unisub._node
    if not sub.length():
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = rope.find(self, sub)
    if pos == -1:
        return space.newtuple([w_self, W_RopeUnicodeObject.EMPTY,
                               W_RopeUnicodeObject.EMPTY])
    else:
        return space.newtuple(
            [W_RopeUnicodeObject(rope.getslice_one(self, 0, pos)),
             w_sub,
             W_RopeUnicodeObject(rope.getslice_one(self, pos + sub.length(),
                                            self.length()))])

def unicode_rpartition__Unicode_Unicode(space, w_unistr, w_unisub):
    # XXX works but flattens
    unistr = w_unistr._node.flatten_unicode()
    unisub = w_unisub._node.flatten_unicode()
    if not unisub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = unistr.rfind(unisub)
    if pos == -1:
        return space.newtuple([W_UnicodeObject.EMPTY,
                               W_UnicodeObject.EMPTY, w_unistr])
    else:
        assert pos > 0
        return space.newtuple([space.wrap(unistr[:pos]), w_unisub,
                               space.wrap(unistr[pos+len(unisub):])])


def unicode_expandtabs__RopeUnicode_ANY(space, w_self, w_tabsize):
    self = w_self._node
    tabsize  = space.int_w(w_tabsize)
    splitted = rope.split(node, rope.LiteralStringNode.PREBUILT[ord('\t')])
    last = splitted[0]
    expanded = [last]
    for i in range(1, len(splitted)):
        expanded.append(rope.multiply(rope.LiteralStringNode.PREBUILT[ord(" ")],
                                      _tabindent(last, tabsize)))
        last = splitted[i]
        expanded.append(last)
    return W_RopeUnicodeObject(rope.rebalance(expanded))

def unicode_translate__RopeUnicode_ANY(space, w_self, w_table):
    self = w_self._node
    w_sys = space.getbuiltinmodule('sys')
    maxunicode = space.int_w(space.getattr(w_sys, space.wrap("maxunicode")))
    result = []
    iter = rope.ItemIterator(self)
    for i in range(self.length()):
        crope = iter.nextrope()
        char = crope.getint(0)
        try:
            w_newval = space.getitem(w_table, space.wrap(char))
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                result.append(crope)
            else:
                raise
        else:
            if space.is_w(w_newval, space.w_None):
                continue
            elif space.is_true(space.isinstance(w_newval, space.w_int)):
                newval = space.int_w(w_newval)
                if newval < 0 or newval > maxunicode:
                    raise OperationError(
                            space.w_TypeError,
                            space.wrap("character mapping must be in range(0x%x)" % (maxunicode + 1,)))
                result.append(unichr(newval))
            elif space.is_true(space.isinstance(w_newval, space.w_unicode)):
                result.append(unicoderope_w(w_newval))
            else:
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("character mapping must return integer, None or unicode"))
    return W_RopeUnicodeObject(rope.join(rope.LiteralStringNode.EMPTY, result))

# Move this into the _codecs module as 'unicodeescape_string (Remember to cater for quotes)'
def repr__RopeUnicode(space, w_unicode):
    hexdigits = "0123456789abcdef"
    chars = w_unicode._node
    size = node.length()
    
    singlequote = doublequote = False
    iter = rope.ItemIterator()
    for i in range(size):
        c = iter.nextunichar()
        if singlequote and doublequote:
            break
        if c == u'\'':
            singlequote = True
        elif c == u'"':
            doublequote = True
    if singlequote and not doublequote:
        quote = '"'
    else:
        quote = '\''
    result = ['u', quote]
    iter = rope.ItemIterator()
    j = 0
    while j < size:
        code = iter.nextint()
        if code >= 0x10000:
            result.extend(['\\', "U",
                           hexdigits[(code >> 28) & 0xf],
                           hexdigits[(code >> 24) & 0xf],
                           hexdigits[(code >> 20) & 0xf],
                           hexdigits[(code >> 16) & 0xf],
                           hexdigits[(code >> 12) & 0xf],
                           hexdigits[(code >>  8) & 0xf],
                           hexdigits[(code >>  4) & 0xf],
                           hexdigits[(code >>  0) & 0xf],
                           ])
            j += 1
            continue
        if code >= 0xD800 and code < 0xDC00:
            if j < size - 1:
                code2 = iter.nextint()
                if code2 >= 0xDC00 and code2 <= 0xDFFF:
                    code = (((code & 0x03FF) << 10) | (code2 & 0x03FF)) + 0x00010000
                    result.extend(["U",
                                   hexdigits[(code >> 28) & 0xf],
                                   hexdigits[(code >> 24) & 0xf],
                                   hexdigits[(code >> 20) & 0xf],
                                   hexdigits[(code >> 16) & 0xf],
                                   hexdigits[(code >> 12) & 0xf],
                                   hexdigits[(code >>  8) & 0xf],
                                   hexdigits[(code >>  4) & 0xf],
                                   hexdigits[(code >>  0) & 0xf],
                                  ])
                    j += 2
                    continue
                
        if code >= 0x100:
            result.extend(['\\', "u",
                           hexdigits[(code >> 12) & 0xf],
                           hexdigits[(code >>  8) & 0xf],
                           hexdigits[(code >>  4) & 0xf],
                           hexdigits[(code >>  0) & 0xf],
                          ])
            j += 1
            continue
        if code == ord('\\') or code == ord(quote):
            result.append('\\')
            result.append(chr(code))
            j += 1
            continue
        if code == ord('\t'):
            result.append('\\')
            result.append('t')
            j += 1
            continue
        if code == ord('\r'):
            result.append('\\')
            result.append('r')
            j += 1
            continue
        if code == ord('\n'):
            result.append('\\')
            result.append('n')
            j += 1
            continue
        if code < ord(' ') or code >= 0x7f:
            result.extend(['\\', "x",
                           hexdigits[(code >> 4) & 0xf], 
                           hexdigits[(code >> 0) & 0xf],
                          ])
            j += 1
            continue
        result.append(chr(code))
        j += 1
    result.append(quote)
    return W_RopeObject(rope.rope_from_charlist(result))

def mod__RopeUnicode_ANY(space, w_format, w_values):
    return mod_format(space, w_format, w_values, do_unicode=True)


import unicodetype
register_all(vars(), unicodetype)

# str.strip(unicode) needs to convert self to unicode and call unicode.strip we
# use the following magic to register strip_string_unicode as a String
# multimethod.

# XXX couldn't string and unicode _share_ the multimethods that make up their
# methods?

class str_methods:
    import stringtype
    W_RopeUnicodeObject = W_RopeUnicodeObject
    from pypy.objspace.std.ropeobject import W_RopeObject
    def str_strip__Rope_RopeUnicode(space, w_self, w_chars):
        return space.call_method(unicode_from_string(space, w_self),
                                 'strip', w_chars)
    def str_lstrip__Rope_RopeUnicode(space, w_self, w_chars):
        return space.call_method(unicode_from_string(space, w_self),
                                 'lstrip', w_chars)
    def str_rstrip__Rope_RopeUnicode(space, w_self, w_chars):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rstrip', w_chars)
    def str_count__Rope_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'count', w_substr, w_start, w_end)
    def str_find__Rope_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'find', w_substr, w_start, w_end)
    def str_rfind__Rope_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rfind', w_substr, w_start, w_end)
    def str_index__Rope_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'index', w_substr, w_start, w_end)
    def str_rindex__Rope_RopeUnicode_ANY_ANY(space, w_self, w_substr, w_start, w_end):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rindex', w_substr, w_start, w_end)
    def str_replace__Rope_RopeUnicode_RopeUnicode_ANY(space, w_self, w_old, w_new, w_maxsplit):
        return space.call_method(unicode_from_string(space, w_self),
                                 'replace', w_old, w_new, w_maxsplit)
    def str_split__Rope_RopeUnicode_ANY(space, w_self, w_delim, w_maxsplit):
        return space.call_method(unicode_from_string(space, w_self),
                                 'split', w_delim, w_maxsplit)
    def str_rsplit__Rope_RopeUnicode_ANY(space, w_self, w_delim, w_maxsplit):
        return space.call_method(unicode_from_string(space, w_self),
                                 'rsplit', w_delim, w_maxsplit)
    register_all(vars(), stringtype)
