from pypy.conftest import gettestobjspace

class AppTestCtypesimport(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ctypes', 'struct'))
        cls.space = space

    def test_import(self):
        import ctypes
        assert ctypes

        import _ctypes
        assert _ctypes
