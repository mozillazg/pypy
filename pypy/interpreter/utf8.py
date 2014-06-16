from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize
from rpython.rlib.runicode import utf8_code_length

MAXUNICODE = 0x10ffff

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
        #       complexity.
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
        if isinstance(c, int):
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
        else:
            # TODO: Only allow ord(c) in [0, 127]
            self._builder.append(c)

    def append_slice(self, s, start, end, is_ascii=False):
        self._builder.append_slice(s, start, end)
        if not is_ascii:
            self._is_ascii = False

    def build(self):
        return Utf8Str(self._builder.build(), self._is_ascii)


# ____________________________________________________________
# Escape-parsing functions

def decode_raw_unicode_escape(s, size, errors, final=False,
                                  errorhandler=None):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    if size == 0:
        # TODO:?
        return Utf8Str('', True), 0

    result = Utf8Builder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            result.append(ch)
            pos += 1
            continue

        # \u-escapes are only interpreted iff the number of leading
        # backslashes is odd
        bs = pos
        while pos < size:
            pos += 1
            if pos == size or s[pos] != '\\':
                break
            result.append('\\')

        # we have a backslash at the end of the string, stop here
        if pos >= size:
            result.append('\\')
            break

        if ((pos - bs) & 1 == 0 or
            pos >= size or
            (s[pos] != 'u' and s[pos] != 'U')):
            result.append('\\')
            result.append(s[pos])
            pos += 1
            continue

        digits = 4 if s[pos] == 'u' else 8
        message = "truncated \\uXXXX"
        pos += 1
        pos = hexescape(result, s, pos, digits,
                        "rawunicodeescape", errorhandler, message, errors)

    return result.build(), pos

# Specialize on the errorhandler when it's a constant
@specialize.arg_or_var(4)
def decode_unicode_escape(s, size, errors, final=False,
                              errorhandler=None,
                              unicodedata_handler=None):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode

    if size == 0:
        return Utf8Str('', True), 0

    builder = Utf8Builder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        # Non-escape characters are interpreted as Unicode ordinals
        if ch != '\\':
            builder.append(ch)
            pos += 1
            continue

        # - Escapes
        pos += 1
        if pos >= size:
            message = "\\ at end of string"
            res, pos = errorhandler(errors, "unicodeescape",
                                    message, s, pos-1, size)
            builder.append(res)
            continue

        ch = s[pos]
        pos += 1
        # \x escapes
        if ch == '\n': pass
        elif ch == '\\': builder.append('\\')
        elif ch == '\'': builder.append('\'')
        elif ch == '\"': builder.append('\"')
        elif ch == 'b' : builder.append('\b')
        elif ch == 'f' : builder.append('\f')
        elif ch == 't' : builder.append('\t')
        elif ch == 'n' : builder.append('\n')
        elif ch == 'r' : builder.append('\r')
        elif ch == 'v' : builder.append('\v')
        elif ch == 'a' : builder.append('\a')
        elif '0' <= ch <= '7':
            x = ord(ch) - ord('0')
            if pos < size:
                ch = s[pos]
                if '0' <= ch <= '7':
                    pos += 1
                    x = (x<<3) + ord(ch) - ord('0')
                    if pos < size:
                        ch = s[pos]
                        if '0' <= ch <= '7':
                            pos += 1
                            x = (x<<3) + ord(ch) - ord('0')
            builder.append(x)
        # hex escapes
        # \xXX
        elif ch == 'x':
            digits = 2
            message = "truncated \\xXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        # \uXXXX
        elif ch == 'u':
            digits = 4
            message = "truncated \\uXXXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        #  \UXXXXXXXX
        elif ch == 'U':
            digits = 8
            message = "truncated \\UXXXXXXXX escape"
            pos = hexescape(builder, s, pos, digits,
                            "unicodeescape", errorhandler, message, errors)

        # \N{name}
        elif ch == 'N':
            message = "malformed \\N character escape"
            look = pos
            if unicodedata_handler is None:
                message = ("\\N escapes not supported "
                           "(can't load unicodedata module)")
                res, pos = errorhandler(errors, "unicodeescape",
                                        message, s, pos-1, size)
                builder.append(res)
                continue

            if look < size and s[look] == '{':
                # look for the closing brace
                while look < size and s[look] != '}':
                    look += 1
                if look < size and s[look] == '}':
                    # found a name.  look it up in the unicode database
                    message = "unknown Unicode character name"
                    name = s[pos+1:look]
                    code = unicodedata_handler.call(name)
                    if code < 0:
                        res, pos = errorhandler(errors, "unicodeescape",
                                                message, s, pos-1, look+1)
                        builder.append(res)
                        continue
                    pos = look + 1
                    builder.append(code)
                else:
                    res, pos = errorhandler(errors, "unicodeescape",
                                            message, s, pos-1, look+1)
                    builder.append(res)
            else:
                res, pos = errorhandler(errors, "unicodeescape",
                                        message, s, pos-1, look+1)
                builder.append(res)
        else:
            builder.append('\\')
            builder.append(ch)

    return builder.build(), pos

hexdigits = "0123456789ABCDEFabcdef"

def hexescape(builder, s, pos, digits,
              encoding, errorhandler, message, errors):
    chr = 0
    if pos + digits > len(s):
        endinpos = pos
        while endinpos < len(s) and s[endinpos] in hexdigits:
            endinpos += 1
        res, pos = errorhandler(errors, encoding,
                                message, s, pos-2, endinpos)
        builder.append(res)
    else:
        try:
            chr = r_uint(int(s[pos:pos+digits], 16))
        except ValueError:
            endinpos = pos
            while s[endinpos] in hexdigits:
                endinpos += 1
            res, pos = errorhandler(errors, encoding,
                                    message, s, pos-2, endinpos)
            builder.append(res)
        else:
            # when we get here, chr is a 32-bit unicode character
            if chr <= MAXUNICODE:
                builder.append(chr)
                pos += digits

            else:
                message = "illegal Unicode character"
                res, pos = errorhandler(errors, encoding,
                                        message, s, pos-2, pos+digits)
                builder.append(res)
    return pos

# ____________________________________________________________

# Converting bytes (utf8) to unicode?
# I guess we just make sure we're looking at valid utf-8 and then make the
# object?

def decode_utf_8(s, size, errors, final=False,
                     errorhandler=None, allow_surrogates=False):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    result = Utf8Builder(size)
    pos = decode_utf_8_impl(s, size, errors, final, errorhandler, result,
                            allow_surrogates=allow_surrogates)
    return result.build(), pos

def decode_utf_8_impl(s, size, errors, final, errorhandler, result,
                      allow_surrogates):
    if size == 0:
        return 0

    # TODO: Instead of assembling and then re-disassembling the codepoints,
    #       just use builder.append_slice
    pos = 0
    while pos < size:
        ordch1 = ord(s[pos])
        # fast path for ASCII
        # XXX maybe use a while loop here
        if ordch1 < 0x80:
            result.append(ordch1)
            pos += 1
            continue

        n = utf8_code_length[ordch1]
        if pos + n > size:
            if not final:
                break
            charsleft = size - pos - 1 # either 0, 1, 2
            # note: when we get the 'unexpected end of data' we don't care
            # about the pos anymore and we just ignore the value
            if not charsleft:
                # there's only the start byte and nothing else
                r, pos = errorhandler(errors, 'utf8',
                                      'unexpected end of data',
                                      s, pos, pos+1)
                result.append(r)
                break
            ordch2 = ord(s[pos+1])
            if n == 3:
                # 3-bytes seq with only a continuation byte
                if (ordch2>>6 != 0x2 or   # 0b10
                    (ordch1 == 0xe0 and ordch2 < 0xa0)):
                    # or (ordch1 == 0xed and ordch2 > 0x9f)
                    # second byte invalid, take the first and continue
                    r, pos = errorhandler(errors, 'utf8',
                                          'invalid continuation byte',
                                          s, pos, pos+1)
                    result.append(r)
                    continue
                else:
                    # second byte valid, but third byte missing
                    r, pos = errorhandler(errors, 'utf8',
                                      'unexpected end of data',
                                      s, pos, pos+2)
                    result.append(r)
                    break
            elif n == 4:
                # 4-bytes seq with 1 or 2 continuation bytes
                if (ordch2>>6 != 0x2 or    # 0b10
                    (ordch1 == 0xf0 and ordch2 < 0x90) or
                    (ordch1 == 0xf4 and ordch2 > 0x8f)):
                    # second byte invalid, take the first and continue
                    r, pos = errorhandler(errors, 'utf8',
                                          'invalid continuation byte',
                                          s, pos, pos+1)
                    result.append(r)
                    continue
                elif charsleft == 2 and ord(s[pos+2])>>6 != 0x2:   # 0b10
                    # third byte invalid, take the first two and continue
                    r, pos = errorhandler(errors, 'utf8',
                                          'invalid continuation byte',
                                          s, pos, pos+2)
                    result.append(r)
                    continue
                else:
                    # there's only 1 or 2 valid cb, but the others are missing
                    r, pos = errorhandler(errors, 'utf8',
                                      'unexpected end of data',
                                      s, pos, pos+charsleft+1)
                    result.append(r)
                    break

        if n == 0:
            r, pos = errorhandler(errors, 'utf8',
                                  'invalid start byte',
                                  s, pos, pos+1)
            result.append(r)

        elif n == 1:
            assert 0, "ascii should have gone through the fast path"

        elif n == 2:
            ordch2 = ord(s[pos+1])
            if ordch2>>6 != 0x2:   # 0b10
                r, pos = errorhandler(errors, 'utf8',
                                      'invalid continuation byte',
                                      s, pos, pos+1)
                result.append(r)
                continue
            # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
            result.append(((ordch1 & 0x1F) << 6) +    # 0b00011111
                           (ordch2 & 0x3F))           # 0b00111111
            pos += 2

        elif n == 3:
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            if (ordch2>>6 != 0x2 or    # 0b10
                (ordch1 == 0xe0 and ordch2 < 0xa0)
                # surrogates shouldn't be valid UTF-8!
                or (not allow_surrogates and ordch1 == 0xed and ordch2 > 0x9f)
                ):
                r, pos = errorhandler(errors, 'utf8',
                                      'invalid continuation byte',
                                      s, pos, pos+1)
                result.append(r)
                continue
            elif ordch3>>6 != 0x2:     # 0b10
                r, pos = errorhandler(errors, 'utf8',
                                      'invalid continuation byte',
                                      s, pos, pos+2)
                result.append(r)
                continue
            # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
            result.append((((ordch1 & 0x0F) << 12) +     # 0b00001111
                           ((ordch2 & 0x3F) << 6) +      # 0b00111111
                            (ordch3 & 0x3F)))            # 0b00111111
            pos += 3

        elif n == 4:
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            ordch4 = ord(s[pos+3])
            if (ordch2>>6 != 0x2 or     # 0b10
                (ordch1 == 0xf0 and ordch2 < 0x90) or
                (ordch1 == 0xf4 and ordch2 > 0x8f)):
                r, pos = errorhandler(errors, 'utf8',
                                      'invalid continuation byte',
                                      s, pos, pos+1)
                result.append(r)
                continue
            elif ordch3>>6 != 0x2:     # 0b10
                r, pos = errorhandler(errors, 'utf8',
                                      'invalid continuation byte',
                                      s, pos, pos+2)
                result.append(r)
                continue
            elif ordch4>>6 != 0x2:     # 0b10
                r, pos = errorhandler(errors, 'utf8',
                                      'invalid continuation byte',
                                      s, pos, pos+3)
                result.append(r)
                continue
            # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
            c = (((ordch1 & 0x07) << 18) +      # 0b00000111
                 ((ordch2 & 0x3F) << 12) +      # 0b00111111
                 ((ordch3 & 0x3F) << 6) +       # 0b00111111
                 (ordch4 & 0x3F))               # 0b00111111

            # TODO: Why doesn't this raise an error when c > MAXUNICODE? If I'm
            #       converting utf8 -> utf8 is this necessary
            if c <= MAXUNICODE:
                result.append(c)
            pos += 4

    return pos

# ____________________________________________________________
# Default error handlers


def default_unicode_error_decode(errors, encoding, msg, s,
                                 startingpos, endingpos):
    if errors == 'replace':
        return _unicode_error_replacement, endingpos
    if errors == 'ignore':
        return '', endingpos
    raise UnicodeDecodeError(encoding, s, startingpos, endingpos, msg)
_unicode_error_replacement = decode_raw_unicode_escape(
    '\ufffd', 1, default_unicode_error_decode)

def default_unicode_error_encode(errors, encoding, msg, u,
                                 startingpos, endingpos):
    if errors == 'replace':
        return '?', None, endingpos
    if errors == 'ignore':
        return '', None, endingpos
    raise UnicodeEncodeError(encoding, u, startingpos, endingpos, msg)

