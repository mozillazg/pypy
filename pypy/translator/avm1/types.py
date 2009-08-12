
from pypy.translator.avm import avm1
from pypy.objspace.flow import model as flowmodel
from pypy.rlib.rarithmetic import r_longlong
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype

_pytype_to_avm1 = {
    str:        avm1.STRING,
    unicode:    avm1.STRING,
    int:        avm1.INTEGER,
    long:       avm1.INTEGER,
    bool:       avm1.BOOLEAN,
    float:      avm1.DOUBLE,
    r_longlong: avm1.INTEGER,
}

class AVM1Number(object):
    pass

class AVM1Primitive(object):
    pass

_lltype_to_avm1 = {
    lltype.Number: AVM1Number,
    lltype.Primitive: AVM1Primitive
}

def pytype_to_avm1(value):
    return (value, _pytype_to_avm1[type(value)])

def lltype_to_avm1(value):
    return _lltype_to_avm1[type(value)]

class AVM1TypeSystem(object):
    def __init__(self, db):
        self.db = db

    def escape_name(self, name):
        return name
    
    def lltype_to_cts(self, TYPE):
        return lltype_to_avm1(TYPE)
    
    def llvar_to_cts(self, var):
        print var.name
        return self.lltype_to_cts(var.concretetype), var.name
