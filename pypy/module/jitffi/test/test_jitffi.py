from pypy.conftest import gettestobjspace
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform

import py

class AppTestJitffi(object):
    @staticmethod
    def preprare_c_example():
        from pypy.tool.udir import udir
        c_file = udir.ensure("test_jitffi", dir=True).join("xlib.c")
        c_file.write(py.code.Source('''
        int add_integers(int a, int b)
        {
           return a+b;
        }
        '''))

        symbols = ["add_integers"]
        eci = ExternalCompilationInfo(export_symbols=symbols)

        return str(platform.compile([c_file], eci, 'x', standalone=False))

    def setup_class(cls):
        from pypy.rlib.libffi import get_libc_name
        space = gettestobjspace(usemodules=('jitffi',))
        cls.space = space
        cls.w_lib_name = space.wrap(cls.preprare_c_example())
        cls.w_libc_name = space.wrap(get_libc_name())

    def test_call(self):
        import jitffi
        lib = jitffi.CDLL(self.lib_name)

        res = lib.call('add_integers', 1, 2)
        assert 3 == res
        res = lib.call('add_integers', -1, 2)
        assert 1 == res
        res = lib.call('add_integers', 0, 0)
        assert 0 == res
