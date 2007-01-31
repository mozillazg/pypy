from pypy.conftest import gettestobjspace

class AppTestPyPyJIT:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space

    def test_setup(self):
        # this just checks that setup() is doing its job correctly, and
        # the resulting code makes sense on top of CPython.
        import pypyjit

        def f(x, y):
            return x*y+1

        assert f(6, 7) == 43
        pypyjit.enable(f.func_code)
        assert f(6, 7) == 43
