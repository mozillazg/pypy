
""" transparent list implementation
"""

from pypy.objspace.std.objspace import *
from pypy.objspace.std.proxy_helpers import register_type
from pypy.interpreter.error import OperationError

class W_Transparent(W_Object):
    def __init__(self, w_controller):
        self.controller = w_controller

class W_TransparentObject(W_Object):
    def __init__(self, w_type, w_controller):
        self.w_type = w_type
        self.w_controller = w_controller
    
    def getclass(self, space):
        return self.w_type
    
    def setclass(self, space, w_subtype):
        raise OperationError(space.w_TypeError,
                             space.wrap("You cannot override __class__ for transparent proxies"))
    
    def getdictvalue(self, space, w_attr):
        try:
            return space.call_function(self.w_controller, space.wrap('__getattribute__'),
               w_attr)
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            return None
    
    def setdictvalue(self, space, w_attr, w_value):
        try:
            space.call_function(self.w_controller, space.wrap('__setattr__'),
               w_attr, w_value)
            return True
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            return False
    
    from pypy.objspace.std.objecttype import object_typedef as typedef

class W_TransparentList(W_Transparent):
    from pypy.objspace.std.listobject import W_ListObject as original
    from pypy.objspace.std.listtype import list_typedef as typedef
    
class W_TransparentDict(W_Transparent):
    from pypy.objspace.std.dictobject import W_DictObject as original
    from pypy.objspace.std.dicttype import dict_typedef as typedef

registerimplementation(W_TransparentList)
registerimplementation(W_TransparentDict)


register_type(W_TransparentList)
register_type(W_TransparentDict)
