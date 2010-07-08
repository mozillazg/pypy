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
