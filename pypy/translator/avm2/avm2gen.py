
""" backend generator routines
"""

from mech.fusion.avm2 import constants, instructions, \
    abc_ as abc, traits, avm2gen, traits

from pypy.objspace.flow import model as flowmodel
from pypy.rlib.rarithmetic import r_int, r_uint, r_longlong, r_ulonglong
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2 import types_ as types, query
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.metavm import Generator
from pypy.translator.oosupport.constant import push_constant

from itertools import chain

class PyPyAvm2ilasm(avm2gen.Avm2ilasm, Generator):

    def __init__(self, db, abc):
        super(PyPyAvm2ilasm, self).__init__(abc)
        self.db = db
        self.cts = db.genoo.TypeSystem(db)

    def _get_type(self, TYPE):
        return self.cts.lltype_to_cts(TYPE)

    def get_class_context(self, name, DICT):
        class_desc = query.Types.get(name, None)
        if class_desc:
            BaseType = class_desc.BaseType
            if '.' in BaseType:
                ns, name = class_desc.BaseType.rsplit('.', 1)
            else:
                ns, name = '', BaseType
            class_desc.super_name = constants.packagedQName(ns, name)
            return class_desc
        else:
            return super(PyPyAvm2ilasm, self).get_class_context(name, DICT)
    
    def load(self, v, *args):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is ootype.Void:
                return # ignore it
            else:
                self.push_local(v)
        elif isinstance(v, flowmodel.Constant):
            push_constant(self.db, v.concretetype, v.value, self)
        else:
            super(PyPyAvm2ilasm, self).load(v)

        for e in args:
            self.load(e)
    
    # def prepare_call_oostring(self, OOTYPE):
    #     self.I(instructions.findpropstrict(types._str_qname))
    
    # def call_oostring(self, OOTYPE):
    #     self.I(instructions.callproperty(types._str_qname, 1))
        
    # call_oounicode = call_oostring
    # prepare_call_oounicode = prepare_call_oostring
    
    def oonewarray(self, TYPE, length=1):
        self.load(types.vec_qname)
        self.load(self.cts.lltype_to_cts(TYPE.ITEM))
        self.I(instructions.applytype(1))
        self.load(length)
        self.I(instructions.construct(1))
        self.I(instructions.coerce(self.cts.lltype_to_cts(TYPE).multiname()))
    
    def push_primitive_constant(self, TYPE, value):
        if TYPE is ootype.Void:
            self.push_null()
        elif TYPE is ootype.String:
            if value._str is None:
                self.push_null()
            else:
                self.push_const(value._str)
        else:
            self.push_const(value)

    def new(self, TYPE):
        # XXX: assume no args for now
        t = self.cts.lltype_to_cts(TYPE).multiname()
        self.emit('findpropstrict', t)
        self.emit('constructprop', t, 0)

    def array_setitem(self, ARRAY=None):
        self.I(instructions.setproperty(constants.MultinameL(
                    constants.PROP_NAMESPACE_SET)))
        # Hack: oosend expects a value to send to StoreResult
        # We don't generate one, push a null.
        self.push_null()

    def array_getitem(self, ARRAY=None):
        self.I(instructions.getproperty(constants.MultinameL(
                    constants.PROP_NAMESPACE_SET)))

    def array_length(self, ARRAY=None):
        self.I(instructions.getproperty(constants.QName("length")))
    
