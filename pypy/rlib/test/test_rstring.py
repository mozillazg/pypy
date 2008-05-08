
from pypy.rlib.rstring import StringBuilder
from 

def test_string_builder():
    s = StringBuilder()
    s.append("a")
    s.append("abc")
    s.append("a")
    assert s.build() == "aabca"
