
""" transparent.py - Several transparent proxy helpers
"""

from pypy.interpreter import gateway
from pypy.interpreter.function import Function
from pypy.interpreter.error import OperationError
from pypy.objspace.std.tlistobject import W_TransparentList

def proxy(space, w_type, w_controller):
    if not space.is_true(space.callable(w_controller)):
        raise OperationError(space.w_TypeError, space.wrap("controller should be function"))
    if not space.is_true(space.issubtype(w_type, space.w_list)):
        raise OperationError(space.w_TypeError, space.wrap("type of object wrapped should be list"))

    return W_TransparentList(w_controller)

app_proxy = gateway.interp2app(proxy, unwrap_spec=[gateway.ObjSpace, gateway.W_Root, \
    gateway.W_Root])
