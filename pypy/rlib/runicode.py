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
        XXX

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

def str_decode_utf8(s, size, errors, final=False,
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
                r, pos = errorhandler(errors, "utf8",
                                      "unexpected end of data", s,  pos, size)
                p += r
        if n == 0:
            res = errorhandler(errors, "utf8", "unexpected code byte",
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
                r, pos = errorhandler(errors, "utf8", "invalid data",
                                      s,  pos, pos + 2)
                p += r
            else:
                c = (y << 6) + z
                if c < 0x80:
                    r, pos = errorhandler(errors, "utf8", "illegal encoding",
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
                r, pos = errorhandler(errors, "utf8", "invalid data",
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
                    r, pos = errorhandler(errors, "utf8", "illegal encoding",
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
                r, pos = errorhandler(errors, "utf8", "invalid data",
                                      s,  pos, pos + 4)
                p += r
            else:
                c = (w << 18) + (x << 12) + (y << 6) + z
                # minimum value allowed for 4 byte encoding
                # maximum value allowed for UTF-16
                if ((c < 0x10000) or (c > 0x10ffff)):
                    r, pos = errorhandler(errors, "utf8", "illegal encoding",
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
            r, pos = errorhandler(errors, "utf8",
                                  "unsupported Unicode code range",
                                  s,  pos, pos + n)
            p += r

    return u"".join(p), pos


def str_decode_latin1(s, size, errors, final=False,
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
