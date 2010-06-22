#! /usr/bin/env python

def fix_lib_python_path():
    """
    This is a (hopefully temporary) hack.

    Currently buildbot assumes runs lib-python tests like this:
    
        python pypy/test_all.py --pypy=pypy/translator/goal/pypy-c \
                                --resultlog=cpython.log lib-python

    However, with the currenct buildbot configuration the tests under lib_pypy
    are never run, so we monkey-patch the command line arguments to add it.    
    """
    import sys
    if sys.argv and sys.argv[-1] == 'lib-python':
        sys.argv.append('lib_pypy')

    
if __name__ == '__main__':
    import tool.autopath
    import py
    fix_lib_python_path()
    py.cmdline.pytest()
