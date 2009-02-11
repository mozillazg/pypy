"""
You need to do a checkout of

         http://codespeak.net/svn/pypy/trunk

in a subdirectory called 'pypy-trunk', or set up a symlink from
'pypy-trunk' to such a checkout.  This conftest.py contains
sys.path magic to use that version of pypy.
"""

import py
rootdir = py.magic.autopath().dirpath()

import sys, os
pypy_trunk = rootdir.join('pypy-trunk')
if not pypy_trunk.check(dir=1):
    raise AssertionError(__doc__)
sys.path.insert(0, str(pypy_trunk))


import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning,
                        module='.*ansi_print')


from pypy.conftest import option


class Directory(py.test.collect.Directory):
    def collect(self):
        # hack to exclude pypy_trunk/
        results = py.test.collect.Directory.collect(self)
        return [item for item in results
                if item.fspath != pypy_trunk]
