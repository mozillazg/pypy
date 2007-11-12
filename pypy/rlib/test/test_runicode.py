from pypy.rlib import runicode

class UnicodeTests(object):
    def typeequals(self, x, y):
        assert x == y
        assert type(x) is type(y)

    def checkdecode(self, s, encoding):
        decoder = getattr(runicode, "str_decode_%s" % encoding)
        trueresult = s.decode(encoding)
        result, consumed = decoder(s, len(s), True)
        assert consumed == len(s)
        self.typeequals(trueresult, result)

class TestDecoding(UnicodeTests):
    
    def test_all_ascii(self):
        for i in range(128):
            self.checkdecode(chr(i), "utf8")

    def test_single_chars(self):
        for s in ["\xd7\x90", "\xd6\x96", "\xeb\x96\x95", "\xf0\x90\x91\x93"]:
            self.checkdecode(s, "utf8")
