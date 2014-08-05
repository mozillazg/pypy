from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import (
    we_are_translated, specialize, import_from_mixin)
from rpython.rlib.runicode import utf8_code_length
from rpython.rlib.unicodedata import unicodedb_5_2_0 as unicodedb
from rpython.rlib.rarithmetic import r_uint, intmask, base_int
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.tool.sourcetools import func_with_new_name


wchar_rint = rffi.r_uint
WCHAR_INTP = rffi.UINTP
WCHAR_INT = rffi.UINT
if rffi.sizeof(rffi.WCHAR_T) == 2:
    wchar_rint = rffi.r_ushort
    WCHAR_INTP = rffi.USHORTP
    WCHAR_INT = rffi.USHORT


def utf8chr(value):
    # Like unichr, but returns a Utf8Str object
    # TODO: Do this without the builder so its faster
    b = Utf8Builder()
    b.append(value)
    return b.build()

def utf8ord_bytes(bytes, start):
    codepoint_length = utf8_code_length[ord(bytes[start])]

    if codepoint_length == 1:
        res = ord(bytes[start])

    elif codepoint_length == 2:
        res = ((ord(bytes[start]) & 0x1F) << 6 |
               (ord(bytes[start + 1]) & 0x3F))
    elif codepoint_length == 3:
        res = ((ord(bytes[start]) & 0xF) << 12 |
               (ord(bytes[start + 1]) & 0x3F) << 6 |
               (ord(bytes[start + 2]) & 0x3F))
    else:
        assert codepoint_length == 4
        res = ((ord(bytes[start]) & 0xF) << 18 |
               (ord(bytes[start + 1]) & 0x3F) << 12 |
               (ord(bytes[start + 2]) & 0x3F) << 6 |
               (ord(bytes[start + 3]) & 0x3F))

    assert res >= 0
    return res

def utf8ord(ustr, start=0):
    start = ustr.index_of_char(start)
    return utf8ord_bytes(ustr.bytes, start)

@specialize.argtype(0)
def ORD(s, pos):
    assert s is not None
    if isinstance(s, Utf8Str):
        return utf8ord(s, pos)
    else:
        return ord(s[pos])

@specialize.argtype(0)
def EQ(s1, s2):
    if s1 is None:
        return s1 is s2
    if isinstance(s1, Utf8Str):
        return s1.__eq__(s2)
    else:
        return s1 == s2

@specialize.argtype(0)
def NE(s1, s2):
    if s1 is None:
        return s1 is not s2
    if isinstance(s1, Utf8Str):
        return s1.__ne__(s2)
    else:
        return s1 != s2

@specialize.argtype(0, 1)
def LT(s1, s2):
    assert s1 is not None
    if isinstance(s1, Utf8Str):
        return s1.__lt__(s2)
    else:
        return s1 < s2

@specialize.argtype(0)
def ADD(s1, s2):
    assert s1 is not None
    if isinstance(s1, Utf8Str):
        return s1.__add__(s2)
    else:
        return s1 + s2

@specialize.argtype(0)
def MUL(s1, s2):
    assert s1 is not None
    if isinstance(s1, Utf8Str):
        return s1.__mul__(s2)
    else:
        assert not isinstance(s1, Utf8Str)
        return s1 * s2

@specialize.argtype(0, 1)
def IN(s1, s2):
    assert s1 is not None
    if isinstance(s2, Utf8Str):
        return s2.__contains__(s1)
    else:
        return s1 in s2

class Utf8Str(object):
    _immutable_fields_ = ['bytes', '_is_ascii', '_len']

    def __init__(self, data, is_ascii=False, length=-1):
        # TODO: Maybe I can determine is_ascii rather than have it passed in?
        #       It really depends on what my model ends up looking like?
        #       It is worth noting that this check can be really fast. We just
        #       have to iterate the bytes while checking for (& 0b01000000)

        self.bytes = data
        self._is_ascii = is_ascii

        if length != -1:
            self._len = length
        else:
            if not is_ascii:
                self._calc_length()
            else:
                self._len = len(data)

    def _calc_length(self):
        pos = 0
        length = 0

        while pos < len(self.bytes):
            length += 1
            pos += utf8_code_length[ord(self.bytes[pos])]

        self._len = length

    def index_of_char(self, char):
        if char >= len(self):
            return len(self.bytes)
        byte = 0
        pos = 0
        while pos < char:
            pos += 1
            byte += utf8_code_length[ord(self.bytes[byte])]

        return byte

    def char_index_of_byte(self, byte_):
        byte = 0
        pos = 0
        while byte < byte_:
            pos += 1
            byte += utf8_code_length[ord(self.bytes[byte])]

        return pos

    def __getitem__(self, char_pos):
        # This if statement is needed for [-1:0] to slice correctly
        if char_pos >= self._len:
            raise IndexError()
        if char_pos < 0:
            char_pos += self._len
        return self[char_pos:char_pos+1]

    @specialize.argtype(1, 2)
    def __getslice__(self, start, stop):
        if start is None:
            start = 0
        if stop is None:
            stop = len(self)

        assert start >= 0
        assert start <= stop

        if start == stop:
            return Utf8Str('')

        if stop > len(self):
            stop = len(self)
        assert stop >= 0

        if self._is_ascii:
            return Utf8Str(self.bytes[start:stop], True)

        start_byte = self.index_of_char(start)
        stop_byte = start_byte
        stop_pos = start
        # TODO: Is detecting ascii-ness here actually useful? If it will
        #       happen in __init__ anyway, maybe its not worth the extra
        #       (code) complexity.
        is_ascii = True
        while stop_pos < stop:
            stop_pos += 1
            increment = utf8_code_length[ord(self.bytes[stop_byte])]
            if increment != 1:
                is_ascii = False
            stop_byte += increment

        return Utf8Str(self.bytes[start_byte:stop_byte], is_ascii,
                       stop - start)

    def byte_slice(self, start, end):
        return Utf8Str(self.bytes[start:end], self._is_ascii)

    def __repr__(self):
        return "<Utf8Str: %r>" % unicode(self)

    def __add__(self, other):
        return Utf8Str(self.bytes + other.bytes,
                       self._is_ascii and other._is_ascii)

    def __mul__(self, count):
        return Utf8Str(self.bytes * count, self._is_ascii)

    def __len__(self):
        assert self._len >= 0
        return self._len

    def __hash__(self):
        return hash(self.bytes)

    def __eq__(self, other):
        if isinstance(other, Utf8Str):
            return self.bytes == other.bytes
        if other is None:
            return False
        if isinstance(other, unicode):
            assert not we_are_translated()
            return unicode(self.bytes, 'utf8') == other

        raise ValueError()

    def __ne__(self, other):
        if isinstance(other, Utf8Str):
            return self.bytes != other.bytes
        if other is None:
            return True
        if isinstance(other, unicode):
            assert not we_are_translated()
            return unicode(self.bytes, 'utf8') != other

        raise ValueError()

    def __lt__(self, other):
        return self.bytes < other.bytes

    def __le__(self, other):
        return self.bytes <= other.bytes

    def __gt__(self, other):
        return self.bytes > other.bytes

    def __ge__(self, other):
        return self.bytes >= other.bytes

    @specialize.argtype(1)
    def __contains__(self, other):
        if isinstance(other, Utf8Str):
            return other.bytes in self.bytes
        if isinstance(other, unicode):
            assert not we_are_translated()
            return other in unicode(self.bytes, 'utf8')
        if isinstance(other, str):
            return other in self.bytes

        raise TypeError()

    def __iter__(self):
        return self.char_iter()

    def __unicode__(self):
        return unicode(self.bytes, 'utf8')

    def char_iter(self):
        return Utf8CharacterIter(self)

    def reverse_char_iter(self):
        return Utf8ReverseCharacterIter(self)

    def codepoint_iter(self):
        return Utf8CodePointIter(self)

    def reverse_codepoint_iter(self):
        return Utf8ReverseCodePointIter(self)

    @specialize.argtype(1, 2)
    def _bound_check(self, start, end):
        if start is None:
            start = 0
        elif start < 0:
            start += len(self)
            if start < 0:
                start = 0
            else:
                start = self.index_of_char(start)
        elif start > len(self):
            start = -1
        else:
            start = self.index_of_char(start)

        if end is None or end >= len(self):
            end = len(self.bytes)
        elif end < 0:
            end += len(self)
            if end < 0:
                end = 0
            else:
                end = self.index_of_char(end)
        elif end > len(self):
            end = len(self.bytes)
        else:
            end = self.index_of_char(end)

        return start, end

    @specialize.argtype(1, 2, 3)
    def find(self, other, start=None, end=None):
        start, end = self._bound_check(start, end)
        if start < 0:
            return -1

        if isinstance(other, Utf8Str):
            pos = self.bytes.find(other.bytes, start, end)
        elif isinstance(other, str):
            pos = self.bytes.find(other, start, end)
        else:
            assert isinstance(other, unicode)
            assert not we_are_translated()
            pos = unicode(self.bytes, 'utf8').find(other, start, end)

        if pos == -1:
            return -1

        return self.char_index_of_byte(pos)

    @specialize.argtype(1, 2, 3)
    def rfind(self, other, start=None, end=None):
        start, end = self._bound_check(start, end)
        if start < 0:
            return -1

        if isinstance(other, Utf8Str):
            pos = self.bytes.rfind(other.bytes, start, end)
        elif isinstance(other, unicode):
            return unicode(self.bytes, 'utf8').rfind(other, start, end)
        else:
            assert isinstance(other, str)
            pos = self.bytes.rfind(other, start, end)

        if pos == -1:
            return -1

        return self.char_index_of_byte(pos)

    @specialize.argtype(1, 2, 3)
    def count(self, other, start=None, end=None):
        start, end = self._bound_check(start, end)
        if start < 0:
            return 0

        if isinstance(other, Utf8Str):
            count = self.bytes.count(other.bytes, start, end)
        elif isinstance(other, unicode):
            return unicode(self.bytes, 'utf8').count(other, start, end)
        else:
            assert isinstance(other, str)
            count = self.bytes.count(other, start, end)

        if count == -1:
            return -1

        return count

    def endswith(self, other):
        return self.rfind(other) == len(self) - len(other)

    @specialize.argtype(1)
    def split(self, other=None, maxsplit=-1):
        if other is not None:
            if isinstance(other, str):
                other_bytes = other
            else:
                assert isinstance(other, Utf8Str)
                other_bytes = other.bytes
            return [Utf8Str(s) for s in self.bytes.split(other_bytes, maxsplit)]

        res = []
        iter = self.codepoint_iter()
        while True:
            # the start of the first word
            for cd in iter:
                if not unicodedb.isspace(cd):
                    break
            else:
                break

            start_byte = iter.byte_pos
            assert start_byte >= 0

            if maxsplit == 0:
                res.append(Utf8Str(self.bytes[start_byte:len(self.bytes)],
                           self._is_ascii))
                break

            for cd in iter:
                if unicodedb.isspace(cd):
                    break
            else:
                # Hit the end of the string
                res.append(Utf8Str(self.bytes[start_byte:len(self.bytes)],
                           self._is_ascii))
                break

            end = iter.byte_pos
            assert end >= 0
            res.append(Utf8Str(self.bytes[start_byte:end], self._is_ascii))
            maxsplit -= 1

        return res

    @specialize.argtype(1)
    def rsplit(self, other=None, maxsplit=-1):
        if other is not None:
            if isinstance(other, str):
                other_bytes = other
            else:
                assert isinstance(other, Utf8Str)
                other_bytes = other.bytes
            return [Utf8Str(s) for s in self.bytes.rsplit(other_bytes, maxsplit)]

        res = []
        iter = self.reverse_codepoint_iter()
        while True:
            # Find the start of the next word
            for cd in iter:
                if not unicodedb.isspace(cd):
                    break
            else:
                break

            start_byte = self.next_char(iter.byte_pos)

            if maxsplit == 0:
                res.append(Utf8Str(self.bytes[0:start_byte], self._is_ascii))
                break

            # Find the end of the word
            for cd in iter:
                if unicodedb.isspace(cd):
                    break
            else:
                # We hit the end of the string
                res.append(Utf8Str(self.bytes[0:start_byte], self._is_ascii))
                break

            end_byte = self.next_char(iter.byte_pos)
            res.append(Utf8Str(self.bytes[end_byte:start_byte],
                               self._is_ascii))
            maxsplit -= 1

        res.reverse()
        return res

    #@specialize.argtype(1)
    def join(self, other):
        if len(other) == 0:
            return Utf8Str('')

        if isinstance(other[0], Utf8Str):
            is_ascii = self._is_ascii
            if is_ascii:
                for s in other:
                    if not s._is_ascii:
                        is_ascii = False
                    break
            return Utf8Str(self.bytes.join([s.bytes for s in other]), is_ascii)
        else:
            assert isinstance(other[0], str)
            return Utf8Str(self.bytes.join([s for s in other]))
    join._annspecialcase_ = 'specialize:arglistitemtype(1)'

    def as_unicode(self):
        """NOT_RPYTHON"""
        return self.bytes.decode('utf-8')

    @staticmethod
    def from_unicode(u):
        """NOT_RPYTHON"""
        return Utf8Str(u.encode('utf-8'))

    def next_char(self, byte_pos):
        assert byte_pos >= 0
        return byte_pos + utf8_code_length[ord(self.bytes[byte_pos])]

    def prev_char(self, byte_pos):
        if byte_pos == 0:
            return -1
        byte_pos -= 1
        while utf8_code_length[ord(self.bytes[byte_pos])] == 0:
            byte_pos -= 1
        return byte_pos

    def copy_to_new_wcharp(self, track_allocation=True):
        length = len(self) + 1
        if rffi.sizeof(rffi.WCHAR_T) == 2:
            for c in self.codepoint_iter():
                if c > 0xFFFF:
                    length += 1

        array = lltype.malloc(WCHAR_INTP.TO, length, flavor='raw',
                              track_allocation=track_allocation)

        self.copy_to_wcharp(array, 0, length)
        array[length - 1] = wchar_rint(0)

        array = rffi.cast(rffi.CWCHARP, array)
        return array

    def copy_to_wcharp(self, dst, dststart, length):
        from pypy.interpreter.utf8_codecs import create_surrogate_pair

        i = 0;
        for c in self.codepoint_iter():
            if i == length:
                break

            if rffi.sizeof(rffi.WCHAR_T) == 2:
                c1, c2 = create_surrogate_pair(c)
                dst[i + dststart] = wchar_rint(c1)
                if c2:
                    i += 1
                    dst[i + dststart] = wchar_rint(c2)
            else:
                dst[i + dststart] = wchar_rint(c)

            i += 1

    def scoped_wcharp_copy(self):
        return WCharContextManager(self)

    @staticmethod
    def from_wcharp(wcharp):
        array = rffi.cast(WCHAR_INTP, wcharp)
        builder = Utf8Builder()
        i = 0;
        while True:
            c = intmask(array[i])
            if c == 0:
                break

            if rffi.sizeof(rffi.WCHAR_T) == 2:
                if 0xD800 <= c <= 0xDBFF:
                    i += 1
                    c2 = intmask(array[i])
                    if c2 == 0:
                        builder.append(c)
                        break
                    elif not (0xDC00 <= c2 <= 0xDFFF):
                        builder.append(c)
                        c = c2
                    else:
                        c = (((c & 0x3FF)<<10) | (c2 & 0x3FF)) + 0x10000;

            builder.append(c)
            i += 1

        return builder.build()

    @staticmethod
    def from_wcharpn(wcharp, size):
        array = rffi.cast(WCHAR_INTP, wcharp)
        builder = Utf8Builder()
        i = 0;
        while i < size:
            c = intmask(array[i])
            if c == 0:
                break

            if rffi.sizeof(rffi.WCHAR_T) == 2:
                if i != size - 1 and 0xD800 <= c <= 0xDBFF:
                    i += 1
                    c2 = intmask(array[i])
                    if c2 == 0:
                        builder.append(c)
                        break
                    elif not (0xDC00 <= c2 <= 0xDFFF):
                        builder.append(c)
                        c = c2
                    else:
                        c = (((c & 0x3FF)<<10) | (c2 & 0x3FF)) + 0x10000;

            builder.append(c)
            i += 1

        return builder.build()

    @staticmethod
    def from_wcharpsize(wcharp, size):
        array = rffi.cast(WCHAR_INTP, wcharp)
        builder = Utf8Builder()
        i = 0;
        while i < size:
            c = intmask(array[i])

            if rffi.sizeof(rffi.WCHAR_T) == 2:
                if i != size - 1 and 0xD800 <= c <= 0xDBFF:
                    i += 1
                    c2 = intmask(array[i])
                    if not (0xDC00 <= c2 <= 0xDFFF):
                        builder.append(c)
                        c = c2
                    else:
                        c = (((c & 0x3FF)<<10) | (c2 & 0x3FF)) + 0x10000;

            builder.append(c)
            i += 1

        return builder.build()

class Utf8Builder(object):
    @specialize.argtype(1)
    def __init__(self, init_size=None):
        if init_size is None:
            self._builder = StringBuilder()
        else:
            self._builder = StringBuilder(init_size)
        self._is_ascii = True
        self._length = 0


    @specialize.argtype(1)
    def append(self, c):
        if isinstance(c, Utf8Str):
            self._builder.append(c.bytes)
            if not c._is_ascii:
                self._is_ascii = False
            self._length += len(c)

        elif isinstance(c, int):
            if c < 0x80:
                self._builder.append(chr(c))
            elif c < 0x800:
                self._builder.append(chr(0xC0 | (c >> 6)))
                self._builder.append(chr(0x80 | (c & 0x3F)))
                self._is_ascii = False
            elif c < 0x10000:
                self._builder.append(chr(0xE0 | (c >> 12)))
                self._builder.append(chr(0x80 | (c >> 6 & 0x3F)))
                self._builder.append(chr(0x80 | (c & 0x3F)))
                self._is_ascii = False
            elif c <= 0x10FFFF:
                self._builder.append(chr(0xF0 | (c >> 18)))
                self._builder.append(chr(0x80 | (c >> 12 & 0x3F)))
                self._builder.append(chr(0x80 | (c >> 6 & 0x3F)))
                self._builder.append(chr(0x80 | (c & 0x3F)))
                self._is_ascii = False
            else:
                raise ValueError("Invalid unicode codepoint > 0x10FFFF.")
            self._length += 1
        else:
            assert isinstance(c, str)
            self._builder.append(c)

            # XXX The assumption here is that the bytes being appended are
            #     ASCII, ie 1:1 byte:char
            self._length += len(c)

    @specialize.argtype(1)
    def append_slice(self, s, start, end):
        if isinstance(s, str):
            self._builder.append_slice(s, start, end)
        elif isinstance(s, Utf8Str):
            self._builder.append_slice(s.bytes, s.index_of_char(start),
                                       s.index_of_char(end))
        else:
            raise TypeError("Invalid type '%s' for Utf8Str.append_slice" %
                            type(s))
        self._length += end - start

    @specialize.argtype(1)
    def append_multiple_char(self, c, count):
        # TODO: What do I do when I have an int? Is it fine to just loop over
        #       .append(c) then? Should (can) I force a resize first?
        if isinstance(c, int):
            self._builder.append_multiple_char(chr(c), count)
            return

        if isinstance(c, str):
            self._builder.append_multiple_char(c, count)
        else:
            self._builder.append_multiple_char(c.bytes, count)
        self._length += count

    def getlength(self):
        return self._length

    def build(self):
        return Utf8Str(self._builder.build(), self._is_ascii)

class WCharContextManager(object):
    def __init__(self, str):
        self.str = str
    def __enter__(self):
        self.data = self.str.copy_to_new_wcharp()
        return self.data
    def __exit__(self, *args):
        rffi.free_wcharp(self.data)

# _______________________________________________

# iter.current is the current (ie the last returned) element
# iter.pos isthe position of the current element
# iter.byte_pos isthe byte position of the current element
# In the before-the-start state, for foward iterators iter.pos and
# iter.byte_pos are -1. For reverse iterators, they are len(ustr) and
# len(ustr.bytes) respectively.

class ForwardIterBase(object):
    def __init__(self, ustr):
        self.ustr = ustr
        self.pos = -1

        self._byte_pos = 0
        self.byte_pos = -1
        self.current = self._default

    def __iter__(self):
        return self

    def next(self):
        if self.pos + 1 == len(self.ustr):
            raise StopIteration()

        self.pos += 1
        self.byte_pos = self._byte_pos

        self.current = self._value(self.byte_pos)

        self._byte_pos = self.ustr.next_char(self._byte_pos)
        return self.current

    def peek_next(self):
        return self._value(self._byte_pos)

    def peek_prev(self):
        return self._value(self._move_backward(self.byte_pos))

    def move(self, count):
        if count > 0:
            self.pos += count

            while count != 1:
                self._byte_pos = self.ustr.next_char(self._byte_pos)
                count -= 1
            self.byte_pos = self._byte_pos
            self._byte_pos = self.ustr.next_char(self._byte_pos)
            self.current = self._value(self.byte_pos)

        elif count < 0:
            self.pos += count
            while count < -1:
                self.byte_pos = self.ustr.prev_char(self.byte_pos)
                count += 1
            self._byte_pos = self.byte_pos
            self.byte_pos = self.ustr.prev_char(self.byte_pos)
            self.current = self._value(self.byte_pos)

    def copy(self):
        iter = self.__class__(self.ustr)
        iter.pos = self.pos
        iter.byte_pos = self.byte_pos
        iter._byte_pos = self._byte_pos
        iter.current = self.current
        return iter

class ReverseIterBase(object):
    def __init__(self, ustr):
        self.ustr = ustr
        self.pos = len(ustr)
        self.byte_pos = len(ustr.bytes)
        self.current = self._default

    def __iter__(self):
        return self

    def next(self):
        if self.pos == 0:
            raise StopIteration()

        self.pos -= 1
        self.byte_pos = self.ustr.prev_char(self.byte_pos)
        self.current = self._value(self.byte_pos)
        return self.current

    def peek_next(self):
        return self._value(self.ustr.prev_char(self.byte_pos))

    def peek_prev(self):
        return self._value(self.ustr.next_char(self.byte_pos))

    def move(self, count):
        if count > 0:
            self.pos -= count
            while count != 0:
                self.byte_pos = self.ustr.prev_char(self.byte_pos)
                count -= 1
            self.current = self._value(self.byte_pos)
        elif count < 0:
            self.pos -= count
            while count != 0:
                self.byte_pos = self.ustr.next_char(self.byte_pos)
                count += 1
            self.current = self._value(self.byte_pos)

    def copy(self):
        iter = self.__class__(self.ustr)
        iter.pos = self.pos
        iter.byte_pos = self.byte_pos
        iter.current = self.current
        return iter

def make_iterator(name, base, calc_value, default):
    class C(object):
        import_from_mixin(base, ['__init__', '__iter__'])
        _default = default
        _value = func_with_new_name(calc_value, '_value')
    C.__name__ = name
    return C

def codepoint_calc_value(self, byte_pos):
    if byte_pos == -1 or byte_pos == len(self.ustr.bytes):
        return -1
    return utf8ord_bytes(self.ustr.bytes, byte_pos)

def character_calc_value(self, byte_pos):
    if byte_pos == -1 or byte_pos == len(self.ustr.bytes):
        return None
    length = utf8_code_length[ord(self.ustr.bytes[self.byte_pos])]
    return Utf8Str(''.join([self.ustr.bytes[i]
                    for i in range(self.byte_pos, self.byte_pos + length)]),
                    length == 1)

Utf8CodePointIter = make_iterator("Utf8CodePointIter", ForwardIterBase,
                                  codepoint_calc_value, -1)
Utf8CharacterIter = make_iterator("Utf8CharacterIter", ForwardIterBase,
                                  character_calc_value, None)
Utf8ReverseCodePointIter = make_iterator(
    "Utf8ReverseCodePointIter", ReverseIterBase, codepoint_calc_value, -1)
Utf8ReverseCharacterIter = make_iterator(
    "Utf8ReverseCharacterIter", ReverseIterBase, character_calc_value, None)

del make_iterator
del codepoint_calc_value
del character_calc_value
del ForwardIterBase
del ReverseIterBase



