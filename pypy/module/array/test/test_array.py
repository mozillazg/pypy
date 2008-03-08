# minimal tests.  See also lib-python/modified-2.4.1/test/test_array.

import py
import struct
from pypy.conftest import gettestobjspace


class AppTestArray:

    def setup_class(cls):
        """
        Create a space with the array module and import it for use by the
        tests.
        """
        cls.space = gettestobjspace(usemodules=['array'])
        cls.w_array = cls.space.appexec([], """():
            import array
            return array
        """)
        cls.w_native_sizes = cls.space.wrap({'l': struct.calcsize('l')})

    def test_attributes(self):
        a = self.array.array('c')
        assert a.typecode == 'c'
        assert a.itemsize == 1
        a = self.array.array('l')
        assert a.typecode == 'l'
        assert a.itemsize == self.native_sizes['l']
