from pypy.conftest import gettestobjspace

class AppTestDotnet:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('clr',))
        cls.space = space

    def test_import_hook_simple(self):
        import clr
        # import System.Math ...

