
""" transparent.py - Several transparent proxy helpers
"""

from pypy.interpreter import gateway
from pypy.interpreter.function import Function
from pypy.interpreter.error import OperationError
from pypy.objspace.std.proxyobject import W_TransparentList, W_TransparentDict,\
    W_Transparent, W_TransparentFunction
from pypy.objspace.std.typeobject import W_TypeObject

def proxy(space, w_type, w_controller):
    from pypy.interpreter.typedef import Function
    
    if not space.is_true(space.callable(w_controller)):
        raise OperationError(space.w_TypeError, space.wrap("controller should be function"))
    
    if isinstance(w_type, W_TypeObject):
        if space.is_true(space.issubtype(w_type, space.w_list)):
            return W_TransparentList(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.w_dict)):
            return W_TransparentDict(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.gettypeobject(Function.typedef))):
            return W_TransparentFunction(space, w_type, w_controller)
        if w_type.instancetypedef is space.w_object.instancetypedef:
            return W_Transparent(space, w_type, w_controller)
    else:
        raise OperationError(space.w_TypeError, space.wrap("type expected as first argument"))
    #return type_cache[w_type or w_type.w_bestbase]
    raise OperationError(space.w_TypeError, space.wrap("Object type %s could not "\
          "be wrapped (YET)" % w_type.getname(space, "?")))

app_proxy = gateway.interp2app(proxy, unwrap_spec=[gateway.ObjSpace, gateway.W_Root, \
    gateway.W_Root])
