
""" transparent list implementation
"""

from pypy.objspace.std.objspace import *
from pypy.objspace.std.proxy_helpers import register_type

class W_TransparentList(W_Object):
    from pypy.objspace.std.listobject import W_ListObject as original
    from pypy.objspace.std.listtype import list_typedef as typedef

    def __init__(self, w_controller):
        self.controller = w_controller

registerimplementation(W_TransparentList)

register_type(W_TransparentList)
