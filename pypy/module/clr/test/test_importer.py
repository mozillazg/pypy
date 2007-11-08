from pypy.conftest import gettestobjspace

class AppTestDotnet:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('clr', ))
        cls.space = space

    def test_import_hook_simple(self):
        import clr
        import System.Math

        assert System.Math.Abs(-5) == 5
        assert System.Math.Pow(2, 5) == 2**5

        Math = clr.load_cli_class('System', 'Math')
        assert Math is System.Math

    def test_ImportError(self):
        skip('Fixme!')
        def fn():
            import non_existent_module
        raises(ImportError, fn())
        
