from pypy.conftest import gettestobjspace

class AppTestDotnet:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('clr', ))
        cls.space = space

    def test_import_hook_simple(self):
        import clr
        import System.Math

        assert System.Math.Abs(-5) == -5
        assert System.Math.Pow(2,5) == 2**5

        # import System.Math ...

