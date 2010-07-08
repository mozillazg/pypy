import py, os
from pypy.conftest import gettestobjspace
from pypy.module.cppyy import interp_cppyy, executor


currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("example01Dict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    os.system("make")

class AppTestPYTHONIFY:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_shared_lib = space.wrap(shared_lib)
        cls.w_example01 = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_lib(%r)""" % (shared_lib, ))

    def testLoadLibCache(self):
        """Test whether loading a library twice results in the same object."""
        import cppyy
        lib2 = cppyy.load_lib(self.shared_lib)
        assert self.example01 is lib2

    def testFindingAClass(self):
        """Test the lookup of a class, and its caching."""
        import cppyy
        example01_class = cppyy.gbl.example01
        cl2 = cppyy.gbl.example01
        assert example01_class is cl2

        raises(AttributeError, "cppyy.gbl.nonexistingclass")

    def testCallingAStaticFunction(self):
        """Test calling of static methods."""
        import cppyy, sys
        example01_class = cppyy.gbl.example01
        res = example01_class.staticAddOneToInt(1)
        assert res == 2

        res = example01_class.staticAddOneToInt(1L)
        assert res == 2
        res = example01_class.staticAddOneToInt(1, 2)
        assert res == 4
        res = example01_class.staticAddOneToInt(-1)
        assert res == 0
        res = example01_class.staticAddOneToInt(sys.maxint-1)
        assert res == sys.maxint
        res = example01_class.staticAddOneToInt(sys.maxint)
        assert res == -sys.maxint-1

        raises(TypeError, 'example01_class.staticAddOneToInt(1, [])')
        raises(TypeError, 'example01_class.staticAddOneToInt(1.)')
        raises(OverflowError, 'example01_class.staticAddOneToInt(sys.maxint+1)')
        res = example01_class.staticAddToDouble(0.09)
        assert res == 0.09 + 0.01

        res = example01_class.staticAtoi("1")
        assert res == 1

        res = example01_class.staticStrcpy("aap")
        assert res == "aap"

        res = example01_class.staticStrcpy(u"aap")
        assert res == "aap"

        raises(TypeError, 'example01_class.staticStrcpy(1.)')

    def test_ConstrucingAndCalling(self):
        """Test object and method calls."""
        import cppyy, sys
        example01_class = cppyy.gbl.example01
        assert example01_class.getCount() == 0
        instance = example01_class(7)
        assert example01_class.getCount() == 1
        res = instance.addDataToInt(4)
        assert res == 11
        res = instance.addDataToInt(-4)
        assert res == 3
        instance.destruct()
        assert example01_class.getCount() == 0
        raises(ReferenceError, 'instance.addDataToInt(4)')
        return

        instance = example01_class(7)
        instance2 = example01_class(8)
        assert example01_class.getCount() == 2
        instance.destruct()
        assert example01_class.getCount() == 1
        instance2.destruct()
        assert example01_class.getCount() == 0

        t = self.example01
        instance = example01_class(13)
        res = instance.addDataToDouble(16)
        assert round(res-29, 8) == 0.
        instance.destruct()
        instance = example01_class(-13)
        res = instance.addDataToDouble(16)
        assert round(res-3, 8) == 0.


        t = self.example01
        instance = example01_class(42)

        res = instance.addDataToAtoi("13")
        assert res == 55

        res = instance.addToStringValue("12")
        assert res == "54"
        res = instance.addToStringValue("-12")
        assert res == "30"
        instance.destruct()
        assert example01_class.getCount() == 0

