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
