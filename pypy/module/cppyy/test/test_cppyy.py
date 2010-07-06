import py
import os
from pypy.conftest import gettestobjspace
from pypy.module.cppyy import interp_cppyy

currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("example01Dict.so"))

space = gettestobjspace(usemodules=['cppyy'])

class TestCPPYYImplementation:
    def test_class_query(self):
        lib = interp_cppyy.load_lib(space, shared_lib)
        w_cppyyclass = lib.type_byname("example01")
        adddouble = w_cppyyclass.function_members["adddouble"]
        func, = adddouble.functions
        assert func.result_type == "double"
        assert func.arg_types == ["double"]


class AppTestCPPYY:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_example01 = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_lib(%r)""" % (shared_lib, ))

    def test_example01static(self):
        t = self.example01.type_byname("example01")
        res = t.invoke("add1", 1)
        assert res == 2

    def test_example01static_double(self):
        t = self.example01.type_byname("example01")
        res = t.invoke("adddouble", 0.09)
        assert res == 0.09 + 0.01

    def test_example01method(self):
        t = self.example01.type_byname("example01")
        count = t.invoke("getcount")
        assert count == 0
        instance = t.construct(7)
        count = t.invoke("getcount")
        assert count == 1
        res = instance.invoke("add", 4)
        assert res == 11
        instance.destruct()
        count = t.invoke("getcount")
        assert count == 0
