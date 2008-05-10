
from pypy.rlib.rstring import StringBuilder, UnicodeBuilder

def test_string_builder():
    s = StringBuilder()
    s.append("a")
    s.append("abc")
    s.append("a")
    assert s.build() == "aabca"

def test_unicode_builder():
    s = UnicodeBuilder()
    s.append(u'a')
    s.append(u'abc')
    s.append(u'abcdef')
    assert s.build() == 'aabcabcdef'
    assert isinstance(s.build(), unicode)
