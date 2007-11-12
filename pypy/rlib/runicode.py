import sys
from pypy.lang.smalltalk.tool.bitmanipulation import splitter

MAXUNICODE = sys.maxunicode


def raise_unicode_exception(errors, encoding, msg, s, startingpos, endingpos,
                            decode=True):
    if decode:
        raise UnicodeDecodeError(
                "%s can't decode byte %s in position %s: %s" % (
                encoding, s[startingpos], startingpos, msg))
    else:
        raise UnicodeEncodeError(
                "%s can't encode byte %s in position %s: %s" % (
                encoding, s[startingpos], startingpos, msg))

# ____________________________________________________________ 
# unicode decoding

utf8_code_length = [
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 0, 0
]

def str_decode_utf_8(s, size, errors, final=False,
                    errorhandler=raise_unicode_exception):
    if (size == 0):
        return u'', 0
    p = []
    pos = 0
    while pos < size:
        ch = s[pos]
        ordch1 = ord(ch)
        if ordch1 < 0x80:
            p += unichr(ordch1)
            pos += 1
            continue

        n = utf8_code_length[ordch1]
        if (pos + n > size):
            if not final:
                break
            else:
                r, pos = errorhandler(errors, "utf-8",
                                      "unexpected end of data", s,  pos, size)
                p += r
                if (pos + n > size):
                    break
        if n == 0:
            res = errorhandler(errors, "utf-8", "unexpected code byte",
                               s,  pos, pos + 1)
            p += res[0]
            pos = res[1]
        elif n == 1:
            assert 0, "you can never get here"
        elif n == 2:
            # 110yyyyy 10zzzzzz   ====>  00000000 00000yyy yyzzzzzz

            ordch2 = ord(s[pos+1])
            z, two = splitter[6, 2](ordch2)
            y, six = splitter[5, 3](ordch1)
            assert six == 6
            if (two != 2):
                r, pos = errorhandler(errors, "utf-8", "invalid data",
                                      s,  pos, pos + 2)
                p += r
            else:
                c = (y << 6) + z
                if c < 0x80:
                    r, pos = errorhandler(errors, "utf-8", "illegal encoding",
                                          s,  pos, pos + 2)
                    p += r
                else:
                    p += unichr(c)
                    pos += n
        elif n == 3:
            #  1110xxxx 10yyyyyy 10zzzzzz ====> 00000000 xxxxyyyy yyzzzzzz
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            z, two1 = splitter[6, 2](ordch3)
            y, two2 = splitter[6, 2](ordch2)
            x, fourteen = splitter[4, 4](ordch1)
            assert fourteen == 14
            if (two1 != 2 or two2 != 2):
                r, pos = errorhandler(errors, "utf-8", "invalid data",
                                      s,  pos, pos + 3)
                p += r
            else:
                c = (x << 12) + (y << 6) + z
                # Note: UTF-8 encodings of surrogates are considered
                # legal UTF-8 sequences;
                # XXX For wide builds (UCS-4) we should probably try
                #     to recombine the surrogates into a single code
                #     unit.
                if c < 0x0800:
                    r, pos = errorhandler(errors, "utf-8", "illegal encoding",
                                          s,  pos, pos + 3)
                    p += r
                else:
                    p += unichr(c)
                    pos += n
        elif n == 4:
            # 11110www 10xxxxxx 10yyyyyy 10zzzzzz ====>
            # 000wwwxx xxxxyyyy yyzzzzzz
            ordch2 = ord(s[pos+1])
            ordch3 = ord(s[pos+2])
            ordch4 = ord(s[pos+3])
            z, two1 = splitter[6, 2](ordch4)
            y, two2 = splitter[6, 2](ordch3)
            x, two3 = splitter[6, 2](ordch2)
            w, thirty = splitter[3, 5](ordch1)
            assert thirty == 30
            if (two1 != 2 or two2 != 2 or two3 != 2):
                r, pos = errorhandler(errors, "utf-8", "invalid data",
                                      s,  pos, pos + 4)
                p += r
            else:
                c = (w << 18) + (x << 12) + (y << 6) + z
                # minimum value allowed for 4 byte encoding
                # maximum value allowed for UTF-16
                if ((c < 0x10000) or (c > 0x10ffff)):
                    r, pos = errorhandler(errors, "utf-8", "illegal encoding",
                                          s,  pos, pos + 4)
                    p += r
                else:
                    # convert to UTF-16 if necessary
                    if c < MAXUNICODE:
                        p.append(unichr(c))
                    else:
                        # compute and append the two surrogates:
                        # translate from 10000..10FFFF to 0..FFFF
                        c -= 0x10000
                        # high surrogate = top 10 bits added to D800
                        p.append(unichr(0xD800 + (c >> 10)))
                        # low surrogate = bottom 10 bits added to DC00
                        p.append(unichr(0xDC00 + (c & 0x03FF)))
                    pos += n
        else:
            r, pos = errorhandler(errors, "utf-8",
                                  "unsupported Unicode code range",
                                  s,  pos, pos + n)
            p += r

    return u"".join(p), pos


def str_decode_utf_16(s, size, errors, final=True,
                     errorhandler=raise_unicode_exception):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "native")
    return result, length

def str_decode_utf_16_be(s, size, errors, final=True,
                       errorhandler=raise_unicode_exception):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "big")
    return result, length

def str_decode_utf_16_le(s, size, errors, final=True,
                         errorhandler=raise_unicode_exception):
    result, length, byteorder = str_decode_utf_16_helper(s, size, errors, final,
                                                         errorhandler, "little")
    return result, length

def str_decode_utf_16_helper(s, size, errors, final=True,
                             errorhandler=raise_unicode_exception,
                             byteorder="native"):

    bo = 0
    consumed = 0

    if sys.byteorder == 'little':
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
    result = []
    if byteorder == 'native':
        if (size >= 2):
            bom = (ord(s[ihi]) << 8) | ord(s[ilo])
            if sys.byteorder == 'little':
                if (bom == 0xFEFF):
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
    if (size == 0):
        return u'', 0, bo
    if (bo == -1):
        # force little endian
        ihi = 1
        ilo = 0

    elif (bo == 1):
        # force big endian
        ihi = 0
        ilo = 1

    #XXX I think the errors are not correctly handled here
    while (pos < len(s)):
        # remaining bytes at the end? (size should be even)
        if len(s) - pos < 2:
            if not final:
                break
            r, pos = errorhandler(errors, 'utf-16', "truncated data",
                                s, pos, len(s), True)
            result.append(r)
            if len(s) - pos < 2:
                break
        ch = (ord(s[pos + ihi]) << 8) | ord(s[pos + ilo])
        pos += 2
        if (ch < 0xD800 or ch > 0xDFFF):
            result += unichr(ch)
            continue
        # UTF-16 code pair:
        if len(s) - pos < 2:
            if not final:
                break
            errmsg = "unexpected end of data"
            r, pos = errorhandler(errors, 'utf-16', errmsg, s, pos - 2, len(s))
            result.append(r)
            if len(s) - pos < 2:
                break
        elif (0xD800 <= ch and ch <= 0xDBFF):
            ch2 = (ord(s[pos+ihi]) << 8) | ord(s[pos+ilo])
            pos += 2
            if (0xDC00 <= ch2 and ch2 <= 0xDFFF):
                if MAXUNICODE < 65536:
                    result += unichr(ch)
                    result += unichr(ch2)
                else:
                    result += unichr((((ch & 0x3FF)<<10) | (ch2 & 0x3FF)) + 0x10000)
                continue
            else:
                r, pos = errorhandler(errors, 'utf-16',
                                      "illegal UTF-16 surrogate",
                                      s, pos - 4, pos - 2)
                result.append(r)
        else:
            assert 0, "unreachable"
    return u"".join(result), pos, bo

def str_decode_latin_1(s, size, errors, final=False,
                      errorhandler=raise_unicode_exception):
    # latin1 is equivalent to the first 256 ordinals in Unicode.
    pos = 0
    p = []
    while (pos < size):
        p += unichr(ord(s[pos]))
        pos += 1
    return u"".join(p), pos


def str_decode_ascii(s, size, errors, final=False,
                     errorhandler=raise_unicode_exception):
    # ASCII is equivalent to the first 128 ordinals in Unicode.
    p = []
    pos = 0
    while pos < len(s):
        c = s[pos]
        if ord(c) < 128:
            p += unichr(ord(c))
            pos += 1
        else:
            r, pos = errorhandler(errors, "ascii", "ordinal not in range(128)",
                                  s,  pos, pos + 1)
            p += r
    return u"".join(p), pos


# ____________________________________________________________ 
# unicode encoding 


def unicode_encode_utf_8(s, size, errors, errorhandler=raise_unicode_exception):
    assert(size >= 0)
    p = []
    i = 0
    while i < size:
        ch = s[i]
        i += 1
        if (ord(ch) < 0x80):
            # Encode ASCII 
            p += chr(ord(ch))
        elif (ord(ch) < 0x0800) :
            # Encode Latin-1 
            p += chr((0xc0 | (ord(ch) >> 6)))
            p += chr((0x80 | (ord(ch) & 0x3f)))
        else:
            # Encode UCS2 Unicode ordinals
            if (ord(ch) < 0x10000):
                # Special case: check for high surrogate
                if (0xD800 <= ord(ch) and ord(ch) <= 0xDBFF and i != size) :
                    ch2 = s[i]
                    # Check for low surrogate and combine the two to
                    # form a UCS4 value
                    if (0xDC00 <= ord(ch2) and ord(ch2) <= 0xDFFF) :
                        ch3 = ((ord(ch) - 0xD800) << 10 | (ord(ch2) - 0xDC00)) + 0x10000
                        i += 1
                        _encodeUCS4(p, ch)
                        continue
                # Fall through: handles isolated high surrogates
                p += (chr((0xe0 | (ord(ch) >> 12))))
                p += (chr((0x80 | ((ord(ch) >> 6) & 0x3f))))
                p += (chr((0x80 | (ord(ch) & 0x3f))))
                continue
            else:
                _encodeUCS4(p, ord(ch))
    return "".join(p)

def _encodeUCS4(p, ch):
    # Encode UCS4 Unicode ordinals
    p +=  (chr((0xf0 | (ch >> 18))))
    p +=  (chr((0x80 | ((ch >> 12) & 0x3f))))
    p +=  (chr((0x80 | ((ch >> 6) & 0x3f))))
    p +=  (chr((0x80 | (ch & 0x3f))))


def unicode_encode_ucs1_helper(p, size, errors,
                               errorhandler=raise_unicode_exception, limit=256):
    if limit == 256:
        reason = "ordinal not in range(256)"
        encoding = "latin-1"
    else:
        reason = "ordinal not in range(128)"
        encoding = "ascii"
    
    if (size == 0):
        return ''
    res = []
    pos = 0
    while pos < len(p):
        ch = p[pos]
        
        if ord(ch) < limit:
            res += chr(ord(ch))
            pos += 1
        else:
            # startpos for collecting unencodable chars
            collstart = pos 
            collend = pos+1 
            while collend < len(p) and ord(p[collend]) >= limit:
                collend += 1
            r, pos = errorhandler(errors, encoding, reason, p,
                                  collstart, collend, False)
            res += r
    
    return "".join(res)

def unicode_encode_latin_1(p, size, errors, errorhandler=raise_unicode_exception):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 256)
    return res

def unicode_encode_ascii(p, size, errors, errorhandler=raise_unicode_exception):
    res = unicode_encode_ucs1_helper(p, size, errors, errorhandler, 128)
    return res


def _STORECHAR(p, CH, byteorder):
    hi = chr(((CH) >> 8) & 0xff)
    lo = chr((CH) & 0xff)
    if byteorder == 'little':
        p.append(lo)
        p.append(hi)
    else:
        p.append(hi)
        p.append(lo)

def unicode_encode_utf_16_helper(s, size, errors,
                                 errorhandler=raise_unicode_exception,
                                 byteorder='little'):
    p = []
    if (byteorder == 'native'):
        _STORECHAR(p, 0xFEFF, sys.byteorder)
        byteorder = sys.byteorder
        
    if size == 0:
        return ""

    i = 0
    while i < size:
        ch = ord(s[i])
        i += 1
        ch2 = 0
        if (ch >= 0x10000) :
            ch2 = 0xDC00 | ((ch-0x10000) & 0x3FF)
            ch  = 0xD800 | ((ch-0x10000) >> 10)

        _STORECHAR(p, ch, byteorder)
        if ch2:
            _STORECHAR(p, ch2, byteorder)

    return "".join(p)

def unicode_encode_utf_16(s, size, errors,
                          errorhandler=raise_unicode_exception):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "native")


def unicode_encode_utf_16_be(s, size, errors,
                           errorhandler=raise_unicode_exception):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "big")


def unicode_encode_utf_16_le(s, size, errors,
                             errorhandler=raise_unicode_exception):
    return unicode_encode_utf_16_helper(s, size, errors, errorhandler, "little")
