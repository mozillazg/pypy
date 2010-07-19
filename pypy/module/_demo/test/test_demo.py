
from pypy.conftest import gettestobjspace

class AppTestDemo(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules = ['_demo'])

    def test_one(self):
        import _demo
        assert repr(_demo.tp(1)) == 'one'
        assert repr(_demo.tp(0)) == 'zero'
        assert len(_demo.tp(1)) == 42

        o0 = _demo.tp(0)
        o1 = _demo.tp(1)
        assert o0.pop(7) == 9
        assert o1.pop(7) == 7
        
        assert type(_demo.tp(1)) is _demo.tp
