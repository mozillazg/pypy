
""" backend generator routines
"""

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2 import constants, instructions, assembler
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.metavm import Generator as OOGenerator
from pypy.translator.oosupport.constant import push_constant
from collections import namedtuple
from itertools import chain

Scope = namedtuple("Scope", "block parent registers namespaces")

_vec_qname = constants.QName("Vector", constants.Namespace(constants.PACKAGE_NAMESPACE, "__AS3__.vec"))
_str_qname = constants.QName("String")
_arr_qname = constants.QName("Array")

class Avm2ilasm(OOGenerator):
    """ AVM2 'assembler' generator routines """
    def __init__(self, asm):
        self.scope = Scope(asm, None, constants.ValuePool("this"), [constants.PACKAGE_NAMESPACE, constants.PRIVATE_NAMESPACE])
        self.constants = constants.AbcConstantPool()
        
    def I(self, *instructions):
        self.scope.block.add(instructions)
    
    @property
    def current_namespaces(self):
        context = self.scope
        namespaces = []
        while context is not None:
            namespaces += context.namespaces
            context = context.parent
        return namespaces
        
    def enter_scope(self, block, registers=['this']):
        self.scope = Scope(block, self.scope, registers)

    def exit_scope(self):
        s = self.scope
        self.scope = self.scope.parent
        return s.block
    
    @property
    def registers(self):
        return self.scope.registers
        
    def pop(self):
        self.I(instructions.pop())

    def dup(self):
        self.I(instructions.dup())

    def swap(self):
        self.I(instructions.swap())

    def emit(self, instr, *args):
        self.I(instructions.INSTRUCTIONS[instr](*args))

    def load(self, v):
        if hasattr(v, "__iter__") and not isinstance(v, basestring):
            for i in v:
                self.load(i)
        elif isinstance(v, flowmodel.Variable):
            if v.concretetype is ootype.Void:
                return # ignore it
            else:
                self.push_local(v)
        elif isinstance(v, flowmodel.Constant):
            push_constant(self.db, v.concretetype, v.value, self)
        else:
            self.push_const(v)

    def store_var(self, v):
        self.I(instrucitons.setlocal(self.registers.index_for(v)))

    def store_local(self, v):
        self.store_var(v.name)

    def call_oostring(self, OOTYPE):
        self.I(instructions.findpropstrict(_str_qname))
        self.swap()
        self.I(instructions.callproperty(_str_qname, 1))
        
    call_oounicode = call_oostring

    def oonewarray(self, TYPE, length=1):
        self.I(instructions.findpropstrict(_arr_qname))
        self.push_const(length)
        self.I(instructions.callproperty(_arr_qname, 1))

    def oonewvector(self, TYPE, length=1):
        self.I(instructions.findpropstrict(_vec_qname))
        self.push_const(
    
    def push_this(self):
        self.I(instructions.getlocal(0))
    
    def push_local(self, v):
        self.push_var(v.name)

    push_arg = push_local

    def push_var(self, v):
        assert v in self.registers
        self.I(instructions.getlocal(self.registers.index_for(v)))

    def push_const(self, v):
        if isinstance(v, int):
            if 0 <= v < 256:
                self.I(instructions.pushbyte(v))
            elif v >= 0:
                self.I(instructions.pushuint(self.constants.uint_pool.index_for(v)))
            else:
                self.I(instructions.pushint(self.constants.int_pool.index_for(v)))
        elif isinstance(v, float):
            self.I(instructions.pushdouble(self.constants.double_pool.index_for(v)))
        elif isinstance(v, basestring):
            self.I(instructions.pushstring(self.constants.utf8_pool.index_for(v)))
        elif v is True:
            self.I(instructions.pushtrue())
        elif v is False:
            self.I(instructions.pushfalse())

    def push_undefined(self):
        self.I(instructions.pushundefined())

    def push_null(self, TYPE=None):
        self.I(instructions.pushnull())

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

    def init_array(self, members=[]):
        self.load(members)
        self.I(instructions.newarray(len(members)))

    def init_object(self, members={}):
        self.load(chain(*members.items()))
        self.I(instructions.newobject(len(members)))
