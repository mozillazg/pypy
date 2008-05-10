
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder

def test_string_builder():
    s = StringBuilder()
    s.append("a")
    s.append("abc")
    s.append("a")
    s.append_slice("abc", 1, 2)
    assert s.build() == "aabcab"

def test_unicode_builder():
    s = UnicodeBuilder()
    s.append(u'a')
    s.append(u'abc')
    s.append_slice(u'abcdef', 1, 2)
    assert s.build() == 'aabcb'
    assert isinstance(s.build(), unicode)
