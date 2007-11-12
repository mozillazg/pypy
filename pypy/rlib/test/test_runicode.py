import sys, random
from pypy.rlib import runicode

class UnicodeTests(object):
    def typeequals(self, x, y):
        assert x == y
        assert type(x) is type(y)

    def checkdecode(self, s, encoding):
        decoder = getattr(runicode, "str_decode_%s" % encoding.replace("-", ""))
        if isinstance(s, str):
            trueresult = s.decode(encoding)
        else:
            trueresult = s
            s = s.encode(encoding)
        result, consumed = decoder(s, len(s), True)
        assert consumed == len(s)
        self.typeequals(trueresult, result)


class TestDecoding(UnicodeTests):
    
    def test_all_ascii(self):
        for i in range(128):
            for encoding in "utf8 latin1 ascii".split():
                self.checkdecode(chr(i), encoding)

    def test_all_first_256(self):
        for i in range(256):
            for encoding in "utf8 latin1 utf16 utf-16-be utf-16-le".split():
                self.checkdecode(unichr(i), encoding)

    def test_random(self):
        for i in range(10000):
            uni = unichr(random.randrange(sys.maxunicode))
            for encoding in "utf8 utf16 utf-16-be utf-16-le".split():
                self.checkdecode(unichr(i), encoding)

    def test_single_chars_utf8(self):
        for s in ["\xd7\x90", "\xd6\x96", "\xeb\x96\x95", "\xf0\x90\x91\x93"]:
            self.checkdecode(s, "utf8")

