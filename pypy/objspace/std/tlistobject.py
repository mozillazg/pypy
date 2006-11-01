
""" transparent list implementation
"""

from pypy.objspace.std.objspace import *
from pypy.objspace.std.proxy_helpers import register_type

class W_Transparent(W_Object):
    def __init__(self, w_controller):
        self.controller = w_controller

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
