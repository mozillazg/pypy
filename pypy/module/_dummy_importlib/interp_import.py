import py
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.module.imp.importing import add_module, check_sys_modules_w


@unwrap_spec(name='text0', level=int)
def importhook(space, name, w_globals=None,
               w_locals=None, w_fromlist=None, level=-1):
    """
    NOT_RPYTHON

    This module is not meant to be translated. As such, we can use all sort of
    non-rpython tricks to implement it :)
    """
    assert level == 0
    if name in space.builtin_modules:
        return space.getbuiltinmodule(name)

    w_path = space.sys.get('path')
    for w_item in space.unpackiterable(w_path):
        item = space.fsdecode_w(w_item)
        d = py.path.local(item)
        pyfile = d.join(name + '.py')
        if pyfile.check(file=True):
            return import_pyfile(space, name, pyfile)


    err = """
    You are using _dummy_importlib: this is not supposed to be a
    fully-compatible importing library, but it contains just enough logic to
    run most of the tests.  If you are experiencing problems with it, consider
    adding more logic, or to switch to the fully-working _frozen_importlib by
    adding this line to your AppTest class:

        spaceconfig = {'usemodules': ['_frozen_importlib']}
    """
    raise OperationError(space.w_ImportError, space.newtext(name + err))
importhook = interp2app(importhook, app_name='__import__')


def import_pyfile(space, modulename, pyfile):
    ec = space.getexecutioncontext()
    source = pyfile.read()
    code_w = ec.compiler.compile(source, str(pyfile), 'exec', 0)
    w_mod = add_module(space, space.newtext(modulename))
    space.setitem(space.sys.get('modules'), w_mod.w_name, w_mod)
    space.setitem(w_mod.w_dict, space.newtext('__name__'), w_mod.w_name)
    code_w.exec_code(space, w_mod.w_dict, w_mod.w_dict)
    assert check_sys_modules_w(space, modulename)
    return w_mod
