from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError


@unwrap_spec(name='text0', level=int)
def importhook(space, name, w_globals=None,
               w_locals=None, w_fromlist=None, level=-1):
    return space.w_None

importhook = interp2app(importhook, app_name='__import__')
