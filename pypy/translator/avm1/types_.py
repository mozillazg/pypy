
from pypy.rlib.rarithmetic import r_longlong, r_ulonglong
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype

from mech.fusion.avm1 import types_, actions

_pytype_to_avm1 = {
    r_longlong:  types_.INTEGER,
    r_ulonglong: types_.INTEGER,
}

_pytype_to_avm1.update(types_._pytype_to_avm1)

def pytype_to_avm1(value):
    return (value, _pytype_to_avm1[type(value)])

def lltype_to_avm1(value):
    return None
    #return _lltype_to_avm1[value]

class AVM1TypeSystem(object):
    def __init__(self, db):
        self.db = db

    def escape_name(self, name):
        return name
    
    def lltype_to_cts(self, TYPE):
        return lltype_to_avm1(TYPE)
    
    def llvar_to_cts(self, var):
        return self.lltype_to_cts(var.concretetype), var.name
