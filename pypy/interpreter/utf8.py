from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize
from rpython.rlib.runicode import utf8_code_length
from rpython.rlib.unicodedata import unicodedb_5_2_0 as unicodedb
from rpython.rlib.rarithmetic import r_uint

def utf8chr(value):
    # Like unichr, but returns a Utf8Str object
    b = Utf8Builder()
    b.append(value)
    return b.build()

def utf8ord_bytes(bytes, start):
    codepoint_length = utf8_code_length[ord(bytes[start])]

    if codepoint_length == 1:
        return ord(bytes[start])

    elif codepoint_length == 2:
        return ((ord(bytes[start]) & 0x1F) << 6 |
                (ord(bytes[start + 1]) & 0x3F))
    elif codepoint_length == 3:
        return ((ord(bytes[start]) & 0xF) << 12 |
                (ord(bytes[start + 1]) & 0x3F) << 6 |
                (ord(bytes[start + 2]) & 0x3F))
    else:
        assert codepoint_length == 4
        return ((ord(bytes[start]) & 0xF) << 18 |
                (ord(bytes[start + 1]) & 0x3F) << 12 |
                (ord(bytes[start + 2]) & 0x3F) << 6 |
                (ord(bytes[start + 3]) & 0x3F))

def utf8ord(ustr, start=0):
    start = ustr.index_of_char(start)
    return utf8ord_bytes(ustr.bytes, start)

@specialize.argtype(0)
def ORD(s, pos):
    if isinstance(s, Utf8Str):
        return utf8ord(s, pos)
    else:
        return ord(s[pos])

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
                #self._len = -1
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

    def __getslice__(self, start, stop):
        assert start <= stop
        if start == stop:
            return Utf8Str('')
        # TODO: If start > _len or stop >= _len, then raise exception 

        if stop > len(self):
            stop = len(self)

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
        return self._len

    def __hash__(self):
        return hash(self.bytes)

    def __eq__(self, other):
        """NOT_RPYTHON"""
        if isinstance(other, Utf8Str):
            return self.bytes == other.bytes
        if isinstance(other, unicode):
            return unicode(self.bytes, 'utf8') == other

        return False

    def __ne__(self, other):
        """NOT_RPYTHON"""
        if isinstance(other, Utf8Str):
            return self.bytes != other.bytes
        if isinstance(other, unicode):
            return unicode(self.bytes, 'utf8') != other

        return True

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
            # TODO: Assert fail if translated
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

    @specialize.argtype(2, 3)
    def find(self, other, start=None, end=None):
        start, end = self._bound_check(start, end)
        if start == -1:
            return -1

        if isinstance(other, Utf8Str):
            pos = self.bytes.find(other.bytes, start, end)
        elif isinstance(other, unicode):
            pos = unicode(self.bytes, 'utf8').find(other, start, end)
        elif isinstance(other, str):
            pos = self.bytes.find(other, start, end)

        if pos == -1:
            return -1

        return self.char_index_of_byte(pos)

    @specialize.argtype(2, 3)
    def rfind(self, other, start=None, end=None):
        start, end = self._bound_check(start, end)
        if start == -1:
            return -1

        if isinstance(other, Utf8Str):
            pos = self.bytes.rfind(other.bytes, start, end)
        elif isinstance(other, unicode):
            return unicode(self.bytes, 'utf8').rfind(other, start, end)
        elif isinstance(other, str):
            pos = self.bytes.rfind(other, start, end)

        if pos == -1:
            return -1

        return self.char_index_of_byte(pos)

    @specialize.argtype(2, 3)
    def count(self, other, start=None, end=None):
        start, end = self._bound_check(start, end)
        if start == -1:
            return 0

        if isinstance(other, Utf8Str):
            count = self.bytes.count(other.bytes, start, end)
        elif isinstance(other, unicode):
            return unicode(self.bytes, 'utf8').count(other, start, end)
        elif isinstance(other, str):
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
            if isinstance(other, Utf8Str):
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

            res.append(Utf8Str(self.bytes[start_byte:iter.byte_pos],
                               self._is_ascii))
            maxsplit -= 1

        return res

    @specialize.argtype(1)
    def rsplit(self, other=None, maxsplit=-1):
        if other is not None:
            if isinstance(other, str):
                other_bytes = other
            if isinstance(other, Utf8Str):
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

    @specialize.argtype(1)
    def join(self, other):
        if len(other) == 0:
            return Utf8Str('')

        if isinstance(other[0], Utf8Str):
            return Utf8Str(
                self.bytes.join([s.bytes for s in other]),
                self._is_ascii and all(s._is_ascii for s in other)
            )
        else:
            return Utf8Str(
                self.bytes.join([s for s in other]),
                self._is_ascii and all(s._is_ascii for s in other)
            )

    def as_unicode(self):
        """NOT_RPYTHON"""
        return self.bytes.decode('utf-8')

    @staticmethod
    def from_unicode(u):
        """NOT_RPYTHON"""
        return Utf8Str(u.encode('utf-8'))

    def next_char(self, byte_pos):
        return byte_pos + utf8_code_length[ord(self.bytes[byte_pos])]

    def prev_char(self, byte_pos):
        if byte_pos == 0:
            return -1
        byte_pos -= 1
        while utf8_code_length[ord(self.bytes[byte_pos])] == 0:
            byte_pos -= 1
        return byte_pos



class Utf8Builder(object):
    @specialize.argtype(1)
    def __init__(self, init_size=None):
        if init_size is None:
            self._builder = StringBuilder()
        else:
            self._builder = StringBuilder(init_size)
        self._is_ascii = True


    @specialize.argtype(1)
    def append(self, c):
        if isinstance(c, int) or isinstance(c, r_uint):
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
        elif isinstance(c, Utf8Str):
            self._builder.append(c.bytes)
            if not c._is_ascii:
                self._is_ascii = False
        else:
            # TODO: Remove this check?
            if len(c) == 1:
                assert ord(c) < 128
            self._builder.append(c)

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

    @specialize.argtype(1)
    def append_multiple_char(self, c, count):
        # TODO: What do I do when I have an int? Is it fine to just loop over
        #       .append(c) then? Should (can) I force a resize first?
        if isinstance(c, int):
            self._builder.append_multiple_char(chr(c), count)
            return

        if len(c) > 1:
            import pdb; pdb.set_trace()
        if isinstance(c, str):
            self._builder.append_multiple_char(c, count)
        else:
            self._builder.append_multiple_char(c.bytes, count)

    def build(self):
        return Utf8Str(self._builder.build(), self._is_ascii)

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
    class C(base):
        _default = default
        _value = calc_value
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
