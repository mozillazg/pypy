from dotviewer.graphparse import *

# XXX mostly empty

def test_re_nonword():
    words = [s for s in re_nonword.split('abc() def2 \\lghi jkl\\l') if s]
    assert words == ['abc', '() ', 'def2', ' \\l', 'ghi', ' ', 'jkl', '\\l']
    words = [s for s in re_nonword.split('abc\\\\def') if s]
    assert words == ['abc', '\\\\', 'def']
