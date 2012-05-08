from pypy.conftest import gettestobjspace

class AppTestJvm:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('jvm',))
        cls.space = space

    def test_app_hello(self):
        import jvm
        res = jvm.app_level_hello('Guido')
        assert 'Guido' in res
        assert 'app-level' in res

    def test_interp_hello(self):
        import jvm
        res = jvm.interp_level_hello('Guido')
        assert 'Guido' in res
        assert 'interp-level' in res
