from pypy.conftest import gettestobjspace

class AppTestDotnet:
    def setup_class(cls):
        # XXX the zipimport below is nonsense, of course, but leaving
        # it out crashes
        space = gettestobjspace(usemodules=('clr', ))
        cls.space = space

    def test_import_hook_simple(self):
        import clr
        import System.Math

        print " abs(-5) = %s"%System.Math.Abs(-5)
        print " 2^5     = %s"%System.Math.Pow(2,5)

        # import System.Math ...

