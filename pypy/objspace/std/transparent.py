
""" transparent.py - Several transparent proxy helpers
"""

from pypy.interpreter import gateway
from pypy.interpreter.function import Function
from pypy.interpreter.error import OperationError
from pypy.objspace.std.tlistobject import W_TransparentList, W_TransparentDict,\
    W_Transparent

def proxy(space, w_type, w_controller):
    if not space.is_true(space.callable(w_controller)):
        raise OperationError(space.w_TypeError, space.wrap("controller should be function"))
    
    if space.is_true(space.issubtype(w_type, space.w_list)):
        return W_TransparentList(space, w_type, w_controller)
    if space.is_true(space.issubtype(w_type, space.w_dict)):
        return W_TransparentDict(space, w_type, w_controller)
    if w_type.instancetypedef is space.w_object.instancetypedef:
       return W_Transparent(space, w_type, w_controller)
    #return type_cache[w_type or w_type.w_bestbase]
    raise OperationError(space.w_TypeError, space.wrap("Object type %s could not"\
          "be wrapped (YET)" % w_type.getname(space, "?")))

app_proxy = gateway.interp2app(proxy, unwrap_spec=[gateway.ObjSpace, gateway.W_Root, \
    gateway.W_Root])
