#! /usr/bin/env python

def fix_lib_python_path():
    """
    This is a (hopefully temporary) hack.

    Currently buildbot assumes that lib-python is under trunk/ and invokes
    lib-python tests like this:
    
        python pypy/test_all.py --pypy=pypy/translator/goal/pypy-c \
                                --resultlog=cpython.log lib-python

    However, now lib-python is under lib/pypy1.2/lib-python.  We cannot just
    change buildbot, as it would break all the other current branches, so
    instead we replace lib-python with the correct path here.
    """
    import sys
    from pypy.tool.lib_pypy import LIB_PYTHON
    if sys.argv and sys.argv[-1].endswith('lib-python'):
        libpython = py.path.local(sys.argv[-1])
        if libpython.check(dir=True):
            # the argument passed to the command line actually exists, so no
            # need to patch it
            return
        else:
            # patch it with the correct path
            sys.argv[-1] = str(LIB_PYTHON)

    
if __name__ == '__main__':
    import tool.autopath
    import py
    fix_lib_python_path()
    py.cmdline.pytest()
