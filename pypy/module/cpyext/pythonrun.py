from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.state import State
from pypy.interpreter import gateway
import os
import pypy

@cpython_api([], rffi.INT_real, error=CANNOT_FAIL)
def Py_IsInitialized(space):
    return 1

@cpython_api([], rffi.CCHARP, error=CANNOT_FAIL)
def Py_GetProgramName(space):
    """
    Return the program name set with Py_SetProgramName(), or the default.
    The returned string points into static storage; the caller should
    not modify its value."""
    return space.fromcache(State).get_programname()

@cpython_api([rffi.CCHARP], lltype.Void, error=CANNOT_FAIL)
def Py_SetProgramName(space, name):
    """
    Set the program name.
    """
    space.fromcache(State).set_programname(name)

@cpython_api([rffi.CCHARP], lltype.Void, error=CANNOT_FAIL)
def Py_SetPythonHome(space, home):
    """
    Set the default "home" directory, that is, the location of the
    standard Python libraries.
    """
    space.fromcache(State).set_pythonhome(home)

@cpython_api([], rffi.CCHARP)
def Py_GetVersion(space):
    """Return the version of this Python interpreter.  This is a
    string that looks something like

    "1.5 (\#67, Dec 31 1997, 22:34:28) [GCC 2.7.2.2]"

    The first word (up to the first space character) is the current
    Python version; the first three characters are the major and minor
    version separated by a period.  The returned string points into
    static storage; the caller should not modify its value.  The value
    is available to Python code as sys.version."""
    return space.fromcache(State).get_version()

@cpython_api([lltype.Ptr(lltype.FuncType([], lltype.Void))], rffi.INT_real, error=-1)
def Py_AtExit(space, func_ptr):
    """Register a cleanup function to be called by Py_Finalize().  The cleanup
    function will be called with no arguments and should return no value.  At
    most 32 cleanup functions can be registered.  When the registration is
    successful, Py_AtExit() returns 0; on failure, it returns -1.  The cleanup
    function registered last is called first. Each cleanup function will be
    called at most once.  Since Python's internal finalization will have
    completed before the cleanup function, no Python APIs should be called by
    func."""
    from pypy.module import cpyext
    w_module = space.getbuiltinmodule('cpyext')
    module = space.interp_w(cpyext.Module, w_module)
    try:
        module.register_atexit(func_ptr)
    except ValueError:
        return -1
    return 0

@cpython_api([], lltype.Void, error=CANNOT_FAIL)
def Py_Finalize(space):
    space.finish()

pypy_init = gateway.applevel('''
def pypy_init(import_site):
    if import_site:
        try:
            import site
        except:
            import sys
            print >> sys.stderr, "import site\' failed"
''').interphook('pypy_init')

@cpython_api([], lltype.Void, error=CANNOT_FAIL)
def _PyPy_Initialize(space):
    srcdir = pypy.__file__
    # set pythonhome/virtualenv
    pyhome = None
    if space.fromcache(State).pythonhome:
        pyhome = rffi.charp2str(space.fromcache(State).pythonhome)
    space.appexec([space.wrap(srcdir), space.wrap(pyhome)], """(srcdir, pyhome):
        import sys
        import os
        if pyhome:
            srcdir = pyhome
        else:
            srcdir = os.path.dirname(os.path.dirname(srcdir))
        sys.pypy_initial_path(srcdir)
    """)
    space.startup()
    space.fromcache(State).startup(space)

    pypy_init(space, space.wrap(True))
