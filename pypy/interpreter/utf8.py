from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize
from rpython.rlib.runicode import utf8_code_length
from rpython.rlib.rarithmetic import r_uint

def utf8chr(value):
    # Like unichr, but returns a Utf8Str object
    b = Utf8Builder()
    b.append(value)
    return b.build()

def utf8ord(ustr, start=0):
    bytes = ustr.bytes
    start = ustr.index_of_char(start)
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

    def __getitem__(self, char_pos):
        # This if statement is needed for [-1:0] to slice correctly
        if char_pos < 0:
            char_pos += self._len
        return self[char_pos:char_pos+1]

    def __getslice__(self, start, stop):
        assert start < stop
        # TODO: If start > _len or stop >= _len, then raise exception 

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

    def __len__(self):
        return self._len

    def __eq__(self, other):
        """NOT_RPYTHON"""
        if isinstance(other, Utf8Str):
            return self.bytes == other.bytes
        if isinstance(other, unicode):
            return unicode(self.bytes, 'utf8') == other

        return False

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
        byte_pos = 0
        while byte_pos < len(self.bytes):
            cplen = utf8_code_length[ord(self.bytes[byte_pos])]
            yield Utf8Str(self.bytes[byte_pos:byte_pos+cplen])
            byte_pos += cplen

    @specialize.argtype(1)
    def find(self, other):
        if isinstance(other, Utf8Str):
            return self.bytes.find(other.bytes)
        if isinstance(other, unicode):
            return unicode(self.bytes, 'utf8').find(other)
        if isinstance(other, str):
            return self.bytes.find(other)

    def rfind(self, other):
        if isinstance(other, Utf8Str):
            return self.bytes.rfind(other.bytes)
        if isinstance(other, unicode):
            return unicode(self.bytes, 'utf8').rfind(other)
        if isinstance(other, str):
            return self.bytes.rfind(other)

    def endswith(self, other):
        return self.rfind(other) == len(self) - len(other)

    def as_unicode(self):
        """NOT_RPYTHON"""
        return self.bytes.decode('utf-8')

    @staticmethod
    def from_unicode(u):
        """NOT_RPYTHON"""
        return Utf8Str(u.encode('utf-8'))

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

    def append_slice(self, s, start, end, is_ascii=False):
        self._builder.append_slice(s, start, end)
        if not is_ascii:
            self._is_ascii = False

    def build(self):
        return Utf8Str(self._builder.build(), self._is_ascii)

