import py
from pypy.tool import lib_pypy

def test_lib_pypy_exists():
    dirname = lib_pypy.get_lib_pypy_dir()
    assert dirname.check(dir=1)

def test_import_from_lib_pypy():
    binascii = lib_pypy.import_from_lib_pypy('binascii')
    assert type(binascii) is type(lib_pypy)
    assert binascii.__name__ == 'lib_pypy.binascii'
    assert hasattr(binascii, 'crc_32_tab')
