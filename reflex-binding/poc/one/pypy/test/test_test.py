from pypy.conftest import gettestobjspace

class AppTestCrypt:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['test'])
    def test_crypt(self):
        import test
        res = test.invokeMethod("testOne")
