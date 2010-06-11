import py
import pypy
import pypy.module
from pypy.module.sys.version import PYPY_VERSION, CPYTHON_VERSION

prefix = py.path.local(pypy.__path__[0]).dirpath()
pypy_ver = 'pypy%d.%d' % PYPY_VERSION[:2]

LIB_ROOT = prefix.join('lib', pypy_ver)
LIB_PYPY =  LIB_ROOT.join('lib_pypy')
LIB_PYTHON = LIB_ROOT.join('lib-python')
LIB_PYTHON_VANILLA = LIB_PYTHON.join('%d.%d.%d' % CPYTHON_VERSION[:3])
LIB_PYTHON_MODIFIED = LIB_PYTHON.join('modified-%d.%d.%d' % CPYTHON_VERSION[:3])

del prefix
del pypy_ver

def import_from_lib_pypy(modname):
    modname = LIB_PYPY.join(modname+'.py')
    return modname.pyimport()
