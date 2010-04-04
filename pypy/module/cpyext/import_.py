from pypy.interpreter import module
from pypy.module.cpyext.api import generic_cpy_call, cpython_api, PyObject
from pypy.interpreter.error import OperationError

@cpython_api([PyObject], PyObject)
def PyImport_Import(space, w_name):
    """
    This is a higher-level interface that calls the current "import hook function".
    It invokes the __import__() function from the __builtins__ of the
    current globals.  This means that the import is done using whatever import hooks
    are installed in the current environment, e.g. by rexec or ihooks.

    Always uses absolute imports."""
    caller = space.getexecutioncontext().gettopframe_nohidden()
    if caller is not None:
        w_globals = caller.w_globals
        try:
            w_builtin = space.getitem(w_globals, space.wrap('__builtins__'))
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
        else:
            if space.is_true(space.isinstance(w_builtin, space.w_dict)):
                 w_builtin = module.Module(space, None, w_builtin)
            builtin = space.interpclass_w(w_builtin)
            if isinstance(builtin, module.Module):
                return space.call(builtin.get("__import__"), space.newtuple([w_name]))
    raise OperationError(space.w_KeyError, space.wrap("__builtins__"))

