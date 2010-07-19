
from pypy.conftest import gettestobjspace

class AppTestDemo(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules = ['_demo'])

    def test_one(self):
        import _demo
        assert repr(_demo.tp(1)) == 'one'
        assert repr(_demo.tp(0)) == 'zero'
