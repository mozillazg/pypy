from pypy.rlib.objectmodel import instantiate
from pypy.lang.io.model import W_Number, W_Object, W_CFunction
import pypy.lang.io.number
from pypy.lang.io.register import cfunction_definitions

class ObjSpace(object):
    """docstring for ObjSpace"""
    def __init__(self):
        self.w_obj = W_Object(self)
        self.w_lobby = W_Object(self)
        self.init_w_number()
        
    def init_w_number(self):
        self.w_number = instantiate(W_Number)
        W_Object.__init__(self.w_number, self)
        self.w_number.value = 0
        for key, function in cfunction_definitions['Number'].items():
            self.w_number.slots[key] = W_CFunction(self, function)