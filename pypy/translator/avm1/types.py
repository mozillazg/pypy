
from pypy.translator.avm import avm1
from pypy.rlib.rarithmetic import r_longlong, r_ulonglong
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype

_pytype_to_avm1 = {
    str:         avm1.STRING,
    unicode:     avm1.STRING,
    int:         avm1.INTEGER,
    long:        avm1.INTEGER,
    r_longlong:  avm1.INTEGER,
    r_ulonglong: avm1.INTEGER,
    bool:        avm1.BOOLEAN,
    float:       avm1.DOUBLE,
}

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
