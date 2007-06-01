
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError

import _curses

class ModuleInfo:
    def __init__(self):
        self.setupterm_called = False

module_info = ModuleInfo()

class curses_error(_curses.error):
    def __init__(self, msg):
        self.args = [msg]

def convert_error(space, error):
    msg = error.args[0]
    w_module = space.getbuiltinmodule('_curses')
    w_exception_class = space.getattr(w_module, space.wrap('error'))
    w_exception = space.call_function(w_exception_class, space.wrap(msg))
    return OperationError(w_exception_class, w_exception)

def _curses_setupterm_null(fd):
    # NOT_RPYTHON
    _curses.setupterm(None, fd)

def _curses_setupterm(termname, fd):
    # NOT_RPYTHON
    _curses.setupterm(termname, fd)

def setupterm(space, w_termname=None, fd=-1):
    if fd == -1:
        w_stdout = space.getattr(space.getbuiltinmodule('sys'),
                                 space.wrap('stdout'))
        fd = space.int_w(space.call_function(space.getattr(w_stdout,
                                             space.wrap('fileno'))))
    try:
        if space.is_w(w_termname, space.w_None) or w_termname is None:
            _curses_setupterm_null(fd)
        else:
            _curses_setupterm(space.str_w(w_termname), fd)
    except _curses.error, e:
        raise convert_error(space, e)
setupterm.unwrap_spec = [ObjSpace, W_Root, int]

class TermError(Exception):
    pass

def _curses_tigetstr(capname):
    # NOT_RPYTHON
    res = _curses.tigetstr(capname)
    if res is None:
        raise TermError
    return res

def _curses_tparm(s, args):
    # NOT_RPYTHON
    return _curses.tparm(s, *args)

def tigetstr(space, capname):
    try:
        result = _curses_tigetstr(capname)
    except TermError:
        return space.w_None
    except _curses.error, e:
        raise convert_error(space, e)
    return space.wrap(result)
tigetstr.unwrap_spec = [ObjSpace, str]

def tparm(space, s, args_w):
    args = [space.int_w(a) for a in args_w]
    try:
        return space.wrap(_curses_tparm(s, args))
    except _curses.error, e:
        raise convert_error(space, e)
tparm.unwrap_spec = [ObjSpace, str, 'args_w']
