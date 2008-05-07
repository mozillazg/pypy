
from pypy.rlib.rstring import StringBuilder

def test_string_builder():
    s = StringBuilder()
    s.append("a")
    s.append("abc")
    s.append_char("a")
    assert s.build() == "aabca"
