import sys

from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib.unicodedata import unicodedb
from rpython.rlib.runicode import utf8_code_length

from pypy.interpreter.utf8 import Utf8Str, Utf8Builder, utf8chr, utf8ord


BYTEORDER = sys.byteorder
MAXUNICODE = 0x10ffff

# ____________________________________________________________
# Unicode escape {{{

# Specialize on the errorhandler when it's a constant
@specialize.arg_or_var(4)
def str_decode_unicode_escape(s, size, errors, final=False,
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

def make_unicode_escape_function(pass_printable=False, unicode_output=False,
                                 quotes=False, prefix=None):
    # Python3 has two similar escape functions: One to implement
    # encode('unicode_escape') and which outputs bytes, and unicode.__repr__
    # which outputs unicode.  They cannot share RPython code, so we generate
    # them with the template below.
    # Python2 does not really need this, but it reduces diffs between branches.

    if unicode_output:
        STRING_BUILDER = Utf8Builder
        STR = Utf8Str
    else:
        STRING_BUILDER = StringBuilder
        STR = str

    def unicode_escape(s, size, errors, errorhandler=None):
        # errorhandler is not used: this function cannot cause Unicode errors
        result = STRING_BUILDER(size)

        if quotes:
            if prefix:
                result.append(prefix)
            if s.find('\'') != -1 and s.find('\"') == -1:
                quote = ord('\"')
                result.append('"')
            else:
                quote = ord('\'')
                result.append('\'')
        else:
            quote = 0

            if size == 0:
                return STR('')

        pos = 0
        while pos < size:
            #oc = ORD(s, pos)
            oc = utf8ord(s, pos)

            # Escape quotes
            if quotes and (oc == quote or oc == ord('\\')):
                result.append('\\')
                result.append(chr(oc))
                pos += 1
                continue

            # Map special whitespace to '\t', \n', '\r'
            if oc == ord('\t'):
                result.append('\\t')
            elif oc == ord('\n'):
                result.append('\\n')
            elif oc == ord('\r'):
                result.append('\\r')
            elif oc == ord('\\'):
                result.append('\\\\')

            # Map non-printable or non-ascii to '\xhh' or '\uhhhh'
            elif pass_printable and not unicodedb.isprintable(oc):
                char_escape_helper(result, oc)
            elif not pass_printable and (oc < 32 or oc >= 0x7F):
                char_escape_helper(result, oc)

            # Copy everything else as-is
            else:
                # TODO: Is this safe? Will we only have ascii characters here?
                result.append(chr(oc))
            pos += 1

        if quotes:
            result.append(chr(quote))
        return result.build()

    def char_escape_helper(result, char):
        num = hex(char)
        if char >= 0x10000:
            result.append("\\U")
            zeros = 8
        elif char >= 0x100:
            result.append("\\u")
            zeros = 4
        else:
            result.append("\\x")
            zeros = 2
        lnum = len(num)
        nb = zeros + 2 - lnum # num starts with '0x'
        if nb > 0:
            result.append_multiple_char('0', nb)
        result.append_slice(num, 2, lnum)

    return unicode_escape, char_escape_helper

# This function is also used by _codecs/interp_codecs.py
(unicode_encode_unicode_escape, raw_unicode_escape_helper
 ) = make_unicode_escape_function()


# }}}

# ____________________________________________________________
# Raw unicode escape {{{

def str_decode_raw_unicode_escape(s, size, errors, final=False,
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

def unicode_encode_raw_unicode_escape(s, size, errors, errorhandler=None):
    # errorhandler is not used: this function cannot cause Unicode errors
    if size == 0:
        return ''
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        oc = utf8ord(s, pos)

        if oc < 0x100:
            result.append(chr(oc))
        else:
            raw_unicode_escape_helper(result, oc)
        pos += 1

    return result.build()

# }}}

# ____________________________________________________________
# ascii & latin-1 {{{

def str_decode_latin_1(s, size, errors, final=False,
                       errorhandler=None):
    # latin1 is equivalent to the first 256 ordinals in Unicode.
    pos = 0
    result = Utf8Builder(size)
    while pos < size:
        result.append(ord(s[pos]))
        pos += 1
    return result.build(), pos


# Specialize on the errorhandler when it's a constant
@specialize.arg_or_var(4)
def str_decode_ascii(s, size, errors, final=False,
                     errorhandler=None):
    # TODO: Is it worth while to try to avoid the making copy by first checking
    #       the string for errors?

    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    # ASCII is equivalent to the first 128 ordinals in Unicode.
    result = Utf8Builder(size)
    pos = 0
    while pos < size:
        c = s[pos]
        if ord(c) < 128:
            result.append(c)
            pos += 1
        else:
            r, pos = errorhandler(errors, "ascii", "ordinal not in range(128)",
                                  s,  pos, pos + 1)
            result.append(r)
    return result.build(), pos


# Specialize on the errorhandler when it's a constant
@specialize.arg_or_var(3)
def unicode_encode_ucs1_helper(p, size, errors,
                               errorhandler=None, limit=256):
    if errorhandler is None:
        errorhandler = default_unicode_error_encode
    if limit == 256:
        reason = "ordinal not in range(256)"
        encoding = "latin-1"
    else:
        reason = "ordinal not in range(128)"
        encoding = "ascii"

    if size == 0:
        return ''
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        od = utf8ord(p, pos)

        if od < limit:
            result.append(chr(od))
            pos += 1
        else:
            # startpos for collecting unencodable chars
            collstart = pos
            collend = pos+1
            while collend < len(p) and utf8ord(p, collend) >= limit:
                collend += 1
            ru, rs, pos = errorhandler(errors, encoding, reason, p,
                                       collstart, collend)
            if rs is not None:
                # py3k only
                result.append(rs)
                continue
            for ch in ru:
                if ord(ch) < limit:
                    result.append(chr(ord(ch)))
                else:
                    errorhandler("strict", encoding, reason, p,
                                 collstart, collend)

    return result.build()

def unicode_encode_latin_1(p, size, errors, errorhandler=None):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 256)
    return res

def unicode_encode_ascii(p, size, errors, errorhandler=None):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 128)
    return res

# }}}

# ____________________________________________________________
# utf-8 {{{

# Converting bytes (utf8) to unicode?
# I guess we just make sure we're looking at valid utf-8 and then make the
# object?

def unicode_encode_utf_8(s, size, errors, errorhandler=None,
                         allow_surrogates=False):
    if size < len(s):
        return s.bytes[0:s.index_of_char(size)]
    return s.bytes

def str_decode_utf_8(s, size, errors, final=False,
                     errorhandler=None, allow_surrogates=False):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    result = Utf8Builder(size)
    pos = str_decode_utf_8_impl(s, size, errors, final, errorhandler, result,
                                allow_surrogates=allow_surrogates)
    return result.build(), pos

def str_decode_utf_8_impl(s, size, errors, final, errorhandler, result,
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

# }}}

# ____________________________________________________________
# utf-16 {{{

def str_decode_utf_16(s, size, errors, final=True,
                      errorhandler=None):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "native")
    return result, length

def str_decode_utf_16_be(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "big")
    return result, length

def str_decode_utf_16_le(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "little")
    return result, length

def str_decode_utf_16_helper(s, size, errors, final=True,
                             errorhandler=None,
                             byteorder="native"):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    bo = 0

    if BYTEORDER == 'little':
        ihi = 1
        ilo = 0
    else:
        ihi = 0
        ilo = 1

    #  Check for BOM marks (U+FEFF) in the input and adjust current
    #  byte order setting accordingly. In native mode, the leading BOM
    #  mark is skipped, in all other modes, it is copied to the output
    #  stream as-is (giving a ZWNBSP character).
    pos = 0
    if byteorder == 'native':
        if size >= 2:
            bom = (ord(s[ihi]) << 8) | ord(s[ilo])
            if BYTEORDER == 'little':
                if bom == 0xFEFF:
                    pos += 2
                    bo = -1
                elif bom == 0xFFFE:
                    pos += 2
                    bo = 1
            else:
                if bom == 0xFEFF:
                    pos += 2
                    bo = 1
                elif bom == 0xFFFE:
                    pos += 2
                    bo = -1
    elif byteorder == 'little':
        bo = -1
    else:
        bo = 1
    if size == 0:
        return u'', 0, bo
    if bo == -1:
        # force little endian
        ihi = 1
        ilo = 0

    elif bo == 1:
        # force big endian
        ihi = 0
        ilo = 1

    result = Utf8Builder(size // 2)

    #XXX I think the errors are not correctly handled here
    while pos < size:
        # remaining bytes at the end? (size should be even)
        if len(s) - pos < 2:
            if not final:
                break
            r, pos = errorhandler(errors, 'utf16', "truncated data",
                                  s, pos, len(s))
            result.append(r)
            if len(s) - pos < 2:
                break
        ch = (ord(s[pos + ihi]) << 8) | ord(s[pos + ilo])
        pos += 2
        if ch < 0xD800 or ch > 0xDFFF:
            result.append(ch)
            continue
        # UTF-16 code pair:
        if len(s) - pos < 2:
            pos -= 2
            if not final:
                break
            errmsg = "unexpected end of data"
            r, pos = errorhandler(errors, 'utf16', errmsg, s, pos, len(s))
            result.append(r)
            if len(s) - pos < 2:
                break
        elif 0xD800 <= ch <= 0xDBFF:
            ch2 = (ord(s[pos+ihi]) << 8) | ord(s[pos+ilo])
            pos += 2
            if 0xDC00 <= ch2 <= 0xDFFF:
                result.append((((ch & 0x3FF)<<10) |
                              (ch2 & 0x3FF)) + 0x10000)
                continue
            else:
                r, pos = errorhandler(errors, 'utf16',
                                      "illegal UTF-16 surrogate",
                                      s, pos - 4, pos - 2)
                result.append(r)
        else:
            r, pos = errorhandler(errors, 'utf16',
                                  "illegal encoding",
                                  s, pos - 2, pos)
            result.append(r)
    return result.build(), pos, bo

def unicode_encode_utf_16_helper(s, size, errors,
                                 errorhandler=None,
                                 byteorder='little'):
    if size == 0:
        if byteorder == 'native':
            result = StringBuilder(2)
            _STORECHAR(result, 0xFEFF, BYTEORDER)
            return result.build()
        return ""

    result = StringBuilder(size * 2 + 2)
    if byteorder == 'native':
        _STORECHAR(result, 0xFEFF, BYTEORDER)
        byteorder = BYTEORDER

    i = 0
    while i < size:
        ch = utf8ord(s, i)
        i += 1
        ch2 = 0
        if ch >= 0x10000:
            ch2 = 0xDC00 | ((ch-0x10000) & 0x3FF)
            ch  = 0xD800 | ((ch-0x10000) >> 10)

        _STORECHAR(result, ch, byteorder)
        if ch2:
            _STORECHAR(result, ch2, byteorder)

    return result.build()

def unicode_encode_utf_16(s, size, errors,
                          errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "native")


def unicode_encode_utf_16_be(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "big")


def unicode_encode_utf_16_le(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "little")

def _STORECHAR(result, CH, byteorder):
    hi = chr(((CH) >> 8) & 0xff)
    lo = chr((CH) & 0xff)
    if byteorder == 'little':
        result.append(lo)
        result.append(hi)
    else:
        result.append(hi)
        result.append(lo)


# }}}

# ____________________________________________________________
# utf-32 {{{

def str_decode_utf_32(s, size, errors, final=True,
                      errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(s, size, errors, final,
                                                         errorhandler, "native")
    return result, length

def str_decode_utf_32_be(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(s, size, errors, final,
                                                         errorhandler, "big")
    return result, length

def str_decode_utf_32_le(s, size, errors, final=True,
                         errorhandler=None):
    result, length, byteorder = str_decode_utf_32_helper(s, size, errors, final,
                                                         errorhandler, "little")
    return result, length

BOM32_DIRECT  = intmask(0x0000FEFF)
BOM32_REVERSE = intmask(0xFFFE0000)

def str_decode_utf_32_helper(s, size, errors, final=True,
                             errorhandler=None,
                             byteorder="native"):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    bo = 0

    if BYTEORDER == 'little':
        iorder = [0, 1, 2, 3]
    else:
        iorder = [3, 2, 1, 0]

    #  Check for BOM marks (U+FEFF) in the input and adjust current
    #  byte order setting accordingly. In native mode, the leading BOM
    #  mark is skipped, in all other modes, it is copied to the output
    #  stream as-is (giving a ZWNBSP character).
    pos = 0
    if byteorder == 'native':
        if size >= 4:
            bom = intmask(
                (ord(s[iorder[3]]) << 24) | (ord(s[iorder[2]]) << 16) |
                (ord(s[iorder[1]]) << 8)  | ord(s[iorder[0]]))
            if BYTEORDER == 'little':
                if bom == BOM32_DIRECT:
                    pos += 4
                    bo = -1
                elif bom == BOM32_REVERSE:
                    pos += 4
                    bo = 1
            else:
                if bom == BOM32_DIRECT:
                    pos += 4
                    bo = 1
                elif bom == BOM32_REVERSE:
                    pos += 4
                    bo = -1
    elif byteorder == 'little':
        bo = -1
    else:
        bo = 1
    if size == 0:
        return u'', 0, bo
    if bo == -1:
        # force little endian
        iorder = [0, 1, 2, 3]

    elif bo == 1:
        # force big endian
        iorder = [3, 2, 1, 0]

    result = Utf8Builder(size // 4)

    while pos < size:
        # remaining bytes at the end? (size should be divisible by 4)
        if len(s) - pos < 4:
            if not final:
                break
            r, pos = errorhandler(errors, 'utf32', "truncated data",
                                  s, pos, len(s))
            result.append(r)
            if len(s) - pos < 4:
                break
            continue
        ch = ((ord(s[pos + iorder[3]]) << 24) | (ord(s[pos + iorder[2]]) << 16) |
              (ord(s[pos + iorder[1]]) << 8)  | ord(s[pos + iorder[0]]))
        if ch >= 0x110000:
            r, pos = errorhandler(errors, 'utf32', "codepoint not in range(0x110000)",
                                  s, pos, len(s))
            result.append(r)
            continue

        result.append(ch)
        pos += 4
    return result.build(), pos, bo

def _STORECHAR32(result, CH, byteorder):
    c0 = chr(((CH) >> 24) & 0xff)
    c1 = chr(((CH) >> 16) & 0xff)
    c2 = chr(((CH) >> 8) & 0xff)
    c3 = chr((CH) & 0xff)
    if byteorder == 'little':
        result.append(c3)
        result.append(c2)
        result.append(c1)
        result.append(c0)
    else:
        result.append(c0)
        result.append(c1)
        result.append(c2)
        result.append(c3)

def unicode_encode_utf_32_helper(s, size, errors,
                                 errorhandler=None,
                                 byteorder='little'):
    if size == 0:
        if byteorder == 'native':
            result = StringBuilder(4)
            _STORECHAR32(result, 0xFEFF, BYTEORDER)
            return result.build()
        return ""

    result = StringBuilder(size * 4 + 4)
    if byteorder == 'native':
        _STORECHAR32(result, 0xFEFF, BYTEORDER)
        byteorder = BYTEORDER

    i = 0
    while i < size:
        ch = utf8ord(s, i)
        i += 1
        ch2 = 0
        if MAXUNICODE < 65536 and 0xD800 <= ch <= 0xDBFF and i < size:
            ch2 = ord(s[i])
            if 0xDC00 <= ch2 <= 0xDFFF:
                ch = (((ch & 0x3FF)<<10) | (ch2 & 0x3FF)) + 0x10000;
                i += 1
        _STORECHAR32(result, ch, byteorder)

    return result.build()

def unicode_encode_utf_32(s, size, errors,
                          errorhandler=None):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler, "native")


def unicode_encode_utf_32_be(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler, "big")


def unicode_encode_utf_32_le(s, size, errors,
                             errorhandler=None):
    return unicode_encode_utf_32_helper(s, size, errors, errorhandler, "little")

# }}}

# ____________________________________________________________
# utf-7 {{{

# Three simple macros defining base-64

def _utf7_IS_BASE64(oc):
    "Is c a base-64 character?"
    c = chr(oc)
    return c.isalnum() or c == '+' or c == '/'
def _utf7_TO_BASE64(n):
    "Returns the base-64 character of the bottom 6 bits of n"
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[n & 0x3f]
def _utf7_FROM_BASE64(c):
    "given that c is a base-64 character, what is its base-64 value?"
    if c >= 'a':
        return ord(c) - 71
    elif c >= 'A':
        return ord(c) - 65
    elif c >= '0':
        return ord(c) + 4
    elif c == '+':
        return 62
    else: # c == '/'
        return 63

def _utf7_DECODE_DIRECT(oc):
    return oc <= 127 and oc != ord('+')

# The UTF-7 encoder treats ASCII characters differently according to
# whether they are Set D, Set O, Whitespace, or special (i.e. none of
# the above).  See RFC2152.  This array identifies these different
# sets:
# 0 : "Set D"
#      alphanumeric and '(),-./:?
# 1 : "Set O"
#     !"#$%&*;<=>@[]^_`{|}
# 2 : "whitespace"
#     ht nl cr sp
# 3 : special (must be base64 encoded)
#     everything else (i.e. +\~ and non-printing codes 0-8 11-12 14-31 127)

utf7_category = [
#  nul soh stx etx eot enq ack bel bs  ht  nl  vt  np  cr  so  si
    3,  3,  3,  3,  3,  3,  3,  3,  3,  2,  2,  3,  3,  2,  3,  3,
#  dle dc1 dc2 dc3 dc4 nak syn etb can em  sub esc fs  gs  rs  us
    3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,
#  sp   !   "   #   $   %   &   '   (   )   *   +   ,   -   .   /
    2,  1,  1,  1,  1,  1,  1,  0,  0,  0,  1,  3,  0,  0,  0,  0,
#   0   1   2   3   4   5   6   7   8   9   :   ;   <   =   >   ?
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  0,
#   @   A   B   C   D   E   F   G   H   I   J   K   L   M   N   O
    1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
#   P   Q   R   S   T   U   V   W   X   Y   Z   [   \   ]   ^   _
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  3,  1,  1,  1,
#   `   a   b   c   d   e   f   g   h   i   j   k   l   m   n   o
    1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
#   p   q   r   s   t   u   v   w   x   y   z   {   |   }   ~  del
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  3,  3,
]

# ENCODE_DIRECT: this character should be encoded as itself.  The
# answer depends on whether we are encoding set O as itself, and also
# on whether we are encoding whitespace as itself.  RFC2152 makes it
# clear that the answers to these questions vary between
# applications, so this code needs to be flexible.

def _utf7_ENCODE_DIRECT(oc, directO, directWS):
    return(oc < 128 and oc > 0 and
           (utf7_category[oc] == 0 or
            (directWS and utf7_category[oc] == 2) or
            (directO and utf7_category[oc] == 1)))

def _utf7_ENCODE_CHAR(result, oc, base64bits, base64buffer):
    if MAXUNICODE > 65535 and oc >= 0x10000:
        # code first surrogate
        base64bits += 16
        base64buffer = (base64buffer << 16) | 0xd800 | ((oc-0x10000) >> 10)
        while base64bits >= 6:
            result.append(_utf7_TO_BASE64(base64buffer >> (base64bits-6)))
            base64bits -= 6
        # prepare second surrogate
        oc = 0xDC00 | ((oc-0x10000) & 0x3FF)
    base64bits += 16
    base64buffer = (base64buffer << 16) | oc
    while base64bits >= 6:
        result.append(_utf7_TO_BASE64(base64buffer >> (base64bits-6)))
        base64bits -= 6
    return base64bits, base64buffer

def str_decode_utf_7(s, size, errors, final=False,
                     errorhandler=None):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    if size == 0:
        return u'', 0

    inShift = False
    base64bits = 0
    base64buffer = 0
    surrogate = 0

    result = Utf8Builder(size)
    pos = 0
    shiftOutStartPos = 0
    while pos < size:
        ch = s[pos]
        oc = ord(ch)

        if inShift: # in a base-64 section
            if _utf7_IS_BASE64(oc): #consume a base-64 character
                base64buffer = (base64buffer << 6) | _utf7_FROM_BASE64(ch)
                base64bits += 6
                pos += 1

                if base64bits >= 16:
                    # enough bits for a UTF-16 value
                    outCh = base64buffer >> (base64bits - 16)
                    base64bits -= 16
                    base64buffer &= (1 << base64bits) - 1 # clear high bits
                    assert outCh <= 0xffff
                    if surrogate:
                        # expecting a second surrogate
                        if outCh >= 0xDC00 and outCh <= 0xDFFFF:
                            result.append((((surrogate & 0x3FF)<<10) |
                                           (outCh & 0x3FF)) + 0x10000)
                            surrogate = 0
                            continue
                        else:
                            result.append(surrogate)
                            surrogate = 0
                            # Not done with outCh: falls back to next line
                    if outCh >= 0xD800 and outCh <= 0xDBFF:
                        # first surrogate
                        surrogate = outCh
                    else:
                        result.append(outCh)

            else:
                # now leaving a base-64 section
                inShift = False
                pos += 1

                if surrogate:
                    result.append(surrogate)
                    surrogate = 0

                if base64bits > 0: # left-over bits
                    if base64bits >= 6:
                        # We've seen at least one base-64 character
                        msg = "partial character in shift sequence"
                        res, pos = errorhandler(errors, 'utf7',
                                                msg, s, pos-1, pos)
                        result.append(res)
                        continue
                    else:
                        # Some bits remain; they should be zero
                        if base64buffer != 0:
                            msg = "non-zero padding bits in shift sequence"
                            res, pos = errorhandler(errors, 'utf7',
                                                    msg, s, pos-1, pos)
                            result.append(res)
                            continue

                if ch == '-':
                    # '-' is absorbed; other terminating characters are
                    # preserved
                    base64bits = 0
                    base64buffer = 0
                    surrogate = 0
                else:
                    result.append(ch)

        elif ch == '+':
            pos += 1 # consume '+'
            if pos < size and s[pos] == '-': # '+-' encodes '+'
                pos += 1
                result.append('+')
            else: # begin base64-encoded section
                inShift = 1
                shiftOutStartPos = pos - 1
                base64bits = 0
                base64buffer = 0

        elif _utf7_DECODE_DIRECT(oc): # character decodes at itself
            result.append(chr(oc))
            pos += 1
        else:
            pos += 1
            msg = "unexpected special character"
            res, pos = errorhandler(errors, 'utf7', msg, s, pos-1, pos)
            result.append(res)

    # end of string

    if inShift and final: # in shift sequence, no more to follow
        # if we're in an inconsistent state, that's an error
        if (surrogate or
            base64bits >= 6 or
            (base64bits > 0 and base64buffer != 0)):
            msg = "unterminated shift sequence"
            res, pos = errorhandler(errors, 'utf7', msg, s, shiftOutStartPos, pos)
            result.append(res)
    elif inShift:
        pos = shiftOutStartPos # back off output

    return result.build(), pos

def unicode_encode_utf_7(s, size, errors, errorhandler=None):
    if size == 0:
        return ''
    result = StringBuilder(size)

    encodeSetO = encodeWhiteSpace = False

    inShift = False
    base64bits = 0
    base64buffer = 0

    # TODO: Looping like this is worse than O(n)
    pos = 0
    while pos < size:
        oc = utf8ord(s, pos)
        if not inShift:
            if oc == ord('+'):
                result.append('+-')
            elif _utf7_ENCODE_DIRECT(oc, not encodeSetO, not encodeWhiteSpace):
                result.append(chr(oc))
            else:
                result.append('+')
                inShift = True
                base64bits, base64buffer = _utf7_ENCODE_CHAR(
                    result, oc, base64bits, base64buffer)
        else:
            if _utf7_ENCODE_DIRECT(oc, not encodeSetO, not encodeWhiteSpace):
                # shifting out
                if base64bits: # output remaining bits
                    result.append(_utf7_TO_BASE64(base64buffer << (6-base64bits)))
                    base64buffer = 0
                    base64bits = 0

                inShift = False
                ## Characters not in the BASE64 set implicitly unshift the
                ## sequence so no '-' is required, except if the character is
                ## itself a '-'
                if _utf7_IS_BASE64(oc) or oc == ord('-'):
                    result.append('-')
                result.append(chr(oc))
            else:
                base64bits, base64buffer = _utf7_ENCODE_CHAR(
                    result, oc, base64bits, base64buffer)
        pos += 1

    if base64bits:
        result.append(_utf7_TO_BASE64(base64buffer << (6 - base64bits)))
    if inShift:
        result.append('-')

    return result.build()

# }}}

# ____________________________________________________________
# Charmap {{{

ERROR_CHAR = u'\ufffe'

@specialize.argtype(5)
def str_decode_charmap(s, size, errors, final=False,
                       errorhandler=None, mapping=None):
    "mapping can be a rpython dictionary, or a dict-like object."

    # Default to Latin-1
    if mapping is None:
        return str_decode_latin_1(s, size, errors, final=final,
                                  errorhandler=errorhandler)
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    if size == 0:
        return u'', 0

    pos = 0
    result = Utf8Builder(size)
    while pos < size:
        ch = s[pos]

        c = mapping.get(ch, ERROR_CHAR)
        if c == ERROR_CHAR:
            r, pos = errorhandler(errors, "charmap",
                                  "character maps to <undefined>",
                                  s,  pos, pos + 1)
            result.append(r)
            continue
        result.append(c)
        pos += 1
    return result.build(), pos

def unicode_encode_charmap(s, size, errors, errorhandler=None,
                           mapping=None):
    if mapping is None:
        return unicode_encode_latin_1(s, size, errors,
                                      errorhandler=errorhandler)

    if errorhandler is None:
        errorhandler = default_unicode_error_encode

    if size == 0:
        return ''
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        ch = s[pos]

        c = mapping.get(ch, '')
        if len(c) == 0:
            ru, rs, pos = errorhandler(errors, "charmap",
                                       "character maps to <undefined>",
                                       s, pos, pos + 1)
            if rs is not None:
                # py3k only
                result.append(rs)
                continue
            for ch2 in ru:
                c2 = mapping.get(ch2, '')
                if len(c2) == 0:
                    errorhandler(
                        "strict", "charmap",
                        "character maps to <undefined>",
                        s,  pos, pos + 1)
                result.append(c2)
            continue
        result.append(c)
        pos += 1
    return result.build()

# }}}

# ____________________________________________________________
# unicode-internal {{{

def str_decode_unicode_internal(s, size, errors, final=False,
                                errorhandler=None):
    if errorhandler is None:
        errorhandler = default_unicode_error_decode
    if size == 0:
        return u'', 0

    if MAXUNICODE < 65536:
        unicode_bytes = 2
    else:
        unicode_bytes = 4
    if BYTEORDER == "little":
        start = 0
        stop = unicode_bytes
        step = 1
    else:
        start = unicode_bytes - 1
        stop = -1
        step = -1

    result = UnicodeBuilder(size // unicode_bytes)
    pos = 0
    while pos < size:
        if pos > size - unicode_bytes:
            res, pos = errorhandler(errors, "unicode_internal",
                                    "truncated input",
                                    s, pos, size)
            result.append(res)
            if pos > size - unicode_bytes:
                break
            continue
        t = r_uint(0)
        h = 0
        for j in range(start, stop, step):
            t += r_uint(ord(s[pos + j])) << (h*8)
            h += 1
        if t > MAXUNICODE:
            res, pos = errorhandler(errors, "unicode_internal",
                                    "unichr(%d) not in range" % (t,),
                                    s, pos, pos + unicode_bytes)
            result.append(res)
            continue
        result.append(UNICHR(t))
        pos += unicode_bytes
    return result.build(), pos

def unicode_encode_unicode_internal(s, size, errors, errorhandler=None):
    if size == 0:
        return ''

    if MAXUNICODE < 65536:
        unicode_bytes = 2
    else:
        unicode_bytes = 4

    result = StringBuilder(size * unicode_bytes)
    pos = 0
    while pos < size:
        oc = utf8ord(s, pos)
        if MAXUNICODE < 65536:
            if BYTEORDER == "little":
                result.append(chr(oc       & 0xFF))
                result.append(chr(oc >>  8 & 0xFF))
            else:
                result.append(chr(oc >>  8 & 0xFF))
                result.append(chr(oc       & 0xFF))
        else:
            if BYTEORDER == "little":
                result.append(chr(oc       & 0xFF))
                result.append(chr(oc >>  8 & 0xFF))
                result.append(chr(oc >> 16 & 0xFF))
                result.append(chr(oc >> 24 & 0xFF))
            else:
                result.append(chr(oc >> 24 & 0xFF))
                result.append(chr(oc >> 16 & 0xFF))
                result.append(chr(oc >>  8 & 0xFF))
                result.append(chr(oc       & 0xFF))
        pos += 1

    return result.build()

# }}}

# ____________________________________________________________
# MBCS codecs for Windows {{{

if sys.platform == 'win32':
    from rpython.rtyper.lltypesystem import lltype, rffi
    from rpython.rlib import rwin32
    CP_ACP = 0
    BOOLP = lltype.Ptr(lltype.Array(rwin32.BOOL, hints={'nolength': True}))

    MultiByteToWideChar = rffi.llexternal('MultiByteToWideChar',
                                          [rffi.UINT, rwin32.DWORD,
                                           rwin32.LPCSTR, rffi.INT,
                                           rffi.CWCHARP, rffi.INT],
                                          rffi.INT,
                                          calling_conv='win')

    WideCharToMultiByte = rffi.llexternal('WideCharToMultiByte',
                                          [rffi.UINT, rwin32.DWORD,
                                           rffi.CWCHARP, rffi.INT,
                                           rwin32.LPCSTR, rffi.INT,
                                           rwin32.LPCSTR, BOOLP],
                                          rffi.INT,
                                          calling_conv='win')

    def is_dbcs_lead_byte(c):
        # XXX don't know how to test this
        return False

    def _decode_mbcs_error(s, errorhandler):
        if rwin32.GetLastError() == rwin32.ERROR_NO_UNICODE_TRANSLATION:
            msg = ("No mapping for the Unicode character exists in the target "
                   "multi-byte code page.")
            errorhandler('strict', 'mbcs', msg, s, 0, 0)
        else:
            raise rwin32.lastWindowsError()

    def str_decode_mbcs(s, size, errors, final=False, errorhandler=None,
                        force_ignore=True):
        if errorhandler is None:
            errorhandler = default_unicode_error_decode

        if not force_ignore and errors not in ('strict', 'ignore'):
            msg = "mbcs encoding does not support errors='%s'" % errors
            errorhandler('strict', 'mbcs', msg, s, 0, 0)

        if size == 0:
            return u"", 0

        if force_ignore or errors == 'ignore':
            flags = 0
        else:
            # strict
            flags = rwin32.MB_ERR_INVALID_CHARS

        # Skip trailing lead-byte unless 'final' is set
        if not final and is_dbcs_lead_byte(s[size-1]):
            size -= 1

        with rffi.scoped_nonmovingbuffer(s) as dataptr:
            # first get the size of the result
            usize = MultiByteToWideChar(CP_ACP, flags,
                                        dataptr, size,
                                        lltype.nullptr(rffi.CWCHARP.TO), 0)
            if usize == 0:
                _decode_mbcs_error(s, errorhandler)

            with rffi.scoped_alloc_unicodebuffer(usize) as buf:
                # do the conversion
                if MultiByteToWideChar(CP_ACP, flags,
                                       dataptr, size, buf.raw, usize) == 0:
                    _decode_mbcs_error(s, errorhandler)
                return buf.str(usize), size

    def unicode_encode_mbcs(s, size, errors, errorhandler=None,
                            force_replace=True):
        if errorhandler is None:
            errorhandler = default_unicode_error_encode

        if not force_replace and errors not in ('strict', 'replace'):
            msg = "mbcs encoding does not support errors='%s'" % errors
            errorhandler('strict', 'mbcs', msg, s, 0, 0)

        if size == 0:
            return ''

        if force_replace or errors == 'replace':
            flags = 0
            used_default_p = lltype.nullptr(BOOLP.TO)
        else:
            # strict
            flags = rwin32.WC_NO_BEST_FIT_CHARS
            used_default_p = lltype.malloc(BOOLP.TO, 1, flavor='raw')
            used_default_p[0] = rffi.cast(rwin32.BOOL, False)

        try:
            with rffi.scoped_nonmoving_unicodebuffer(s) as dataptr:
                # first get the size of the result
                mbcssize = WideCharToMultiByte(CP_ACP, flags,
                                               dataptr, size, None, 0,
                                               None, used_default_p)
                if mbcssize == 0:
                    raise rwin32.lastWindowsError()
                # If we used a default char, then we failed!
                if (used_default_p and
                    rffi.cast(lltype.Bool, used_default_p[0])):
                    errorhandler('strict', 'mbcs', "invalid character",
                                 s, 0, 0)

                with rffi.scoped_alloc_buffer(mbcssize) as buf:
                    # do the conversion
                    if WideCharToMultiByte(CP_ACP, flags,
                                           dataptr, size, buf.raw, mbcssize,
                                           None, used_default_p) == 0:
                        raise rwin32.lastWindowsError()
                    if (used_default_p and
                        rffi.cast(lltype.Bool, used_default_p[0])):
                        errorhandler('strict', 'mbcs', "invalid character",
                                     s, 0, 0)
                    return buf.str(mbcssize)
        finally:
            if used_default_p:
                lltype.free(used_default_p, flavor='raw')

# }}}

# ____________________________________________________________
# Decimal Encoder {{{

def unicode_encode_decimal(s, size, errors, errorhandler=None):
    """Converts whitespace to ' ', decimal characters to their
    corresponding ASCII digit and all other Latin-1 characters except
    \0 as-is. Characters outside this range (Unicode ordinals 1-256)
    are treated as errors. This includes embedded NULL bytes.
    """
    if errorhandler is None:
        errorhandler = default_unicode_error_encode
    if size == 0:
        return ''
    result = StringBuilder(size)
    pos = 0
    while pos < size:
        ch = ord(s[pos])
        if unicodedb.isspace(ch):
            result.append(' ')
            pos += 1
            continue
        try:
            decimal = unicodedb.decimal(ch)
        except KeyError:
            pass
        else:
            result.append(chr(48 + decimal))
            pos += 1
            continue
        if 0 < ch < 256:
            result.append(chr(ch))
            pos += 1
            continue
        # All other characters are considered unencodable
        collstart = pos
        collend = collstart + 1
        while collend < size:
            ch = ord(s[collend])
            try:
                if (0 < ch < 256 or
                    unicodedb.isspace(ch) or
                    unicodedb.decimal(ch) >= 0):
                    break
            except KeyError:
                # not a decimal
                pass
            collend += 1
        msg = "invalid decimal Unicode string"
        ru, rs, pos = errorhandler(errors, 'decimal',
                                   msg, s, collstart, collend)
        if rs is not None:
            # py3k only
            errorhandler('strict', 'decimal', msg, s, collstart, collend)
        for char in ru:
            ch = ord(char)
            if unicodedb.isspace(ch):
                result.append(' ')
                continue
            try:
                decimal = unicodedb.decimal(ch)
            except KeyError:
                pass
            else:
                result.append(chr(48 + decimal))
                continue
            if 0 < ch < 256:
                result.append(chr(ch))
                continue
            errorhandler('strict', 'decimal',
                         msg, s, collstart, collend)
    return result.build()

# }}}

# ____________________________________________________________
# Default error handlers

def default_unicode_error_decode(errors, encoding, msg, s,
                                 startingpos, endingpos):
    if errors == 'replace':
        return _unicode_error_replacement, endingpos
    if errors == 'ignore':
        return '', endingpos
    raise UnicodeDecodeError(encoding, s, startingpos, endingpos, msg)
_unicode_error_replacement = Utf8Str.from_unicode(u'\ufffd')

def default_unicode_error_encode(errors, encoding, msg, u,
                                 startingpos, endingpos):
    if errors == 'replace':
        return '?', None, endingpos
    if errors == 'ignore':
        return '', None, endingpos
    raise UnicodeEncodeError(encoding, u, startingpos, endingpos, msg)

