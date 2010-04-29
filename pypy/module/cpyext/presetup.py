
""" A distutils-patching tool that allows testing CPython extensions without
building pypy-c.

Run python <this file> setup.py build in your project directory

You can import resulting .so with py.py --allworingmodules
"""

import sys, os
dn = os.path.dirname
rootdir = dn(dn(dn(dn(__file__))))
sys.path.insert(0, rootdir)
pypydir = os.path.join(rootdir, 'pypy')
f = open(os.path.join(pypydir, '_interfaces', 'pyconfig.h'), "w")
f.write("\n")
f.close()
sys.path.insert(0, os.getcwd())
from distutils import sysconfig

from pypy.tool.udir import udir
from pypy.conftest import gettestobjspace
from pypy.module.cpyext.api import setup_library
space = gettestobjspace(usemodules=['cpyext', 'thread'])
setup_library(space)

inc_paths = str(udir)

def get_python_inc(plat_specific=0, prefix=None):
    if plat_specific:
        return os.path.join(pypydir, '_interfaces')
    return os.path.join(os.path.dirname(__file__), 'include')

def patch_distutils():
    sysconfig.get_python_inc = get_python_inc

# unconditionally, since it's supposed to be run as PYTHONSTARTUP
patch_distutils()

del sys.argv[0]
execfile(sys.argv[0])
