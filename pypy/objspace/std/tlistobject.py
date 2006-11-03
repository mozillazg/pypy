
""" transparent list implementation
"""

from pypy.objspace.std.objspace import *
from pypy.objspace.std.proxy_helpers import register_type
from pypy.interpreter.error import OperationError
from pypy.interpreter import baseobjspace

#class W_Transparent(W_Object):
#    def __init__(self, w_controller):
#        self.controller = w_controller

class W_Transparent(W_Object):
    def __init__(self, space, w_type, w_controller):
        self.w_type = w_type
        self.w_controller = w_controller
        self.space = space
    
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
    
    def deldictvalue(self, space, w_attr):
        try:
            space.call_function(self.w_controller, space.wrap('__delattr__'),
               w_attr)
            return True
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            return False
    
    def getdict(self):
        return self.getdictvalue(self.space, self.space.wrap('__dict__'))
    
    def setdict(self, space, w_dict):
        if not self.setdictvalue(space, space.wrap('__dict__'), w_dict):
            baseobjspace.W_Root.setdict(self, space, w_dict)

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
