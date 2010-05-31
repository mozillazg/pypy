import py
from pypy.tool import lib_pypy

def test_lib_pypy_exists():
    dirname = lib_pypy.get_lib_pypy_dir()
    assert dirname.check(dir=1)
