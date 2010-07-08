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

