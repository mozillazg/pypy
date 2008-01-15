from pypy.conftest import gettestobjspace
import os, sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestNested:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_rawffi','struct'))
        cls.space = space

    def test_inspect_structure(self):
        import _rawffi, struct
        align = max(struct.calcsize("i"), struct.calcsize("P"))
        assert align & (align-1) == 0, "not a power of 2??"
        def round_up(x):
            return (x+align-1) & -align

        S = _rawffi.Structure([('a', 'i'), ('b', 'P'), ('c', 'c')])
        assert S.size == round_up(struct.calcsize("iPc"))
        assert S.alignment == align
        assert S.getfieldoffset('a') == 0
        assert S.getfieldoffset('b') == align
        assert S.getfieldoffset('c') == round_up(struct.calcsize("iP"))
        assert S.gettypecode() == (S.size, S.alignment)

    def test_nested_structures(self):
        import _rawffi
        S1 = _rawffi.Structure([('a', 'i'), ('b', 'P'), ('c', 'c')])
        S = _rawffi.Structure([('x', 'c'), ('s1', S1.gettypecode())])
        assert S.size == S1.alignment + S1.size
        assert S.alignment == S1.alignment
        assert S.getfieldoffset('x') == 0
        assert S.getfieldoffset('s1') == S1.alignment
        s = S()
        s.x = 'G'
        raises(TypeError, 's.s1')
        assert s.fieldaddress('s1') == s.buffer + S.getfieldoffset('s1')
        s1 = S1.fromaddress(s.fieldaddress('s1'))
        s1.c = 'H'
        rawbuf = _rawffi.Array('c').fromaddress(s.buffer, S.size)
        assert rawbuf[0] == 'G'
        assert rawbuf[S1.alignment + S1.getfieldoffset('c')] == 'H'
        s.free()
