from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestArrayModule(AppTestCpythonExtensionBase):
    def test_basic(self):
        module = self.import_module(name='array')
        arr = module.array('i', [1,2,3])
        assert arr.typecode == 'i'
        assert arr.itemsize == 4
        assert arr[2] == 3
        assert len(arr.buffer_info()) == 2
        arr.append(4)
        assert arr.tolist() == [1, 2, 3, 4]
        assert len(arr) == 4
