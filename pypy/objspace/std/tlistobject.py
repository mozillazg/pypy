
""" transparent list implementation
"""

from pypy.objspace.std.objspace import *

class W_TransparentList(W_Object):
    from pypy.objspace.std.listtype import list_typedef as typedef

    def __init__(self, w_controller):
        self.controller = w_controller

registerimplementation(W_TransparentList)

def repr__TransparentList(space, w_transparent_list):
    return space.call_function(w_transparent_list.controller, space.wrap("__repr__"))

def list_append__TransparentList_ANY(space, w_transparent_list, w_any):
    space.call_function(w_transparent_list.controller, space.wrap("append"), w_any)
    return space.w_None

def list_extend__TransparentList_ANY(space, w_list, w_any):
    space.call_function(w_transparent_list.controller, space.wrap("extend"), w_any)
    return space.w_None

def lt__TransparentList_ANY(space, w_transparent_list, w_list):
    return space.call_function(w_transparent_list.controller, space.wrap("__lt__"), w_list)

def gt__TransparentList_ANY(space, w_transparent_list, w_list):
    return space.call_function(w_transparent_list.controller, space.wrap("__gt__"), w_list)

def iter__TransparentList(space, w_transparent_list):
    return space.call_function(w_transparent_list.controller, space.wrap("__iter__"))

from pypy.objspace.std import listtype
register_all(vars(), listtype)
