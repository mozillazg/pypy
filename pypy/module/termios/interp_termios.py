
""" Termios module. I'm implementing it directly here, as I see
little use of termios module on RPython level by itself
"""

from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rpython.module import ll_termios
import os
import termios

# proper semantics are to have termios.error, but since it's not documented
# anyway, let's have it as OSError on interplevel. We need to have
# some details what is missing in RPython modules though

def convert_error(space, error):
    errno = error.errno
    w_module = space.getbuiltinmodule('termios')
    w_exception_class = space.getattr(w_module, space.wrap('error'))
    try:
        msg = os.strerror(errno)
    except ValueError:
        msg = 'error %d' % errno
    w_exception = space.call_function(w_exception_class, space.wrap(errno),
                                      space.wrap(msg))
    return OperationError(w_exception_class, w_exception)

def tcsetattr(space, fd, when, w_attributes):
    pass
tcsetattr.unwrap_spec = [ObjSpace, int, int, W_Root]

def tcgetattr(space, fd):
    try:
        tup = termios.tcgetattr(fd)
    except termios.error, e:
        e.errno = e.args[0]
        raise convert_error(space, e)
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = tup
    l_w = [space.wrap(i) for i in [iflag, oflag, cflag, lflag, ispeed, ospeed]]
    # last one need to be chosen carefully
    w_cc = space.newlist([space.wrap(i) for i in cc])
    l_w.append(w_cc)
    return space.newlist(l_w)
tcgetattr.unwrap_spec = [ObjSpace, int]

def tcsendbreak(space, fd, duration):
    pass
tcsendbreak.unwrap_spec = [ObjSpace, int, int]

def tcdrain(space, fd, duration):
    pass
tcdrain.unwrap_spec = [ObjSpace, int, int]

def tcflush(space, fd, queue):
    pass
tcflush.unwrap_spec = [ObjSpace, int, int]

def tcflow(space, fd, action):
    pass
tcflow.unwrap_spec = [ObjSpace, int, int]
