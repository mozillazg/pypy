import py
import os
from pypy.conftest import gettestobjspace

currpath = py.path.local(__file__).dirpath()

class AppTestCPPYY:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['cppyy'])
        env = os.environ
        cls.w_example01 = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_lib(%r)""" % (str(currpath.join("example01Dict.so")), ))

    def test_example01static(self):
        t = self.example01.type_byname("example01")
        res = t.invoke("add1", 1)
        assert res == 2

    def test_example01method(self):
        t = self.example01.type_byname("example01")
        instance = t.construct(7)
        res = instance.invoke("add", 4)
        assert res == 11
