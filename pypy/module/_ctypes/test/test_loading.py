from pypy.conftest import gettestobjspace

import sys
import os

import py


class AppTestLoader(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ctypes',))
        cls.space = space
        cls.w_unknowndll = space.wrap("xxrandomnamexx")

        from ctypes.util import find_library
        libc_name = None
        if os.name == "nt":
            libc_name = "msvcrt"
        elif os.name == "ce":
            libc_name = "coredll"
        elif sys.platform == "cygwin":
            libc_name = "cygwin1.dll"
        else:
            libc_name = find_library("c")
        cls.w_libc_name = space.wrap(libc_name)

    def test_load(self):
        if self.libc_name is None:
            skip("Libc not found")

        import os
        from ctypes import CDLL
        CDLL(self.libc_name)
        CDLL(os.path.basename(self.libc_name))
        raises(OSError, CDLL, self.unknowndll)

    def test_load_version(self):
        import os
        if self.libc_name is None \
                or os.path.basename(self.libc_name) != "libc.so.6":
            skip("Libc not found or wrong libc name")

        from ctypes import cdll
        cdll.LoadLibrary("libc.so.6")
        # linux uses version, libc 9 should not exist
        raises(OSError, cdll.LoadLibrary, "libc.so.9")
        raises(OSError, cdll.LoadLibrary, self.unknowndll)

    def test_find(self):
        from ctypes import cdll, CDLL
        from ctypes.util import find_library
        for name in ("c", "m"):
            lib = find_library(name)
            if lib:
                cdll.LoadLibrary(lib)
                CDLL(lib)

    def test_load_library(self):
        import os
        if os.name not in ("nt", "ce"):
            skip('test is platform dependent')

        if os.name == "nt":
            windll.kernel32.GetModuleHandleW
            windll["kernel32"].GetModuleHandleW
            windll.LoadLibrary("kernel32").GetModuleHandleW
            WinDLL("kernel32").GetModuleHandleW
        elif os.name == "ce":
            windll.coredll.GetModuleHandleW
            windll["coredll"].GetModuleHandleW
            windll.LoadLibrary("coredll").GetModuleHandleW
            WinDLL("coredll").GetModuleHandleW

    def test_load_ordinal_functions(self):
        import os
        if os.name not in ("nt", "ce"):
            skip('test is platform dependent')

        import conftest
        _ctypes_test = str(conftest.sofile)
        dll = CDLL(_ctypes_test)
        # We load the same function both via ordinal and name
        func_ord = dll[2]
        func_name = dll.GetString
        # addressof gets the address where the function pointer is stored
        a_ord = addressof(func_ord)
        a_name = addressof(func_name)
        f_ord_addr = c_void_p.from_address(a_ord).value
        f_name_addr = c_void_p.from_address(a_name).value
        assert hex(f_ord_addr) == hex(f_name_addr)

        raises(AttributeError, dll.__getitem__, 1234)
