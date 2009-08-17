
""" backend generator routines
"""

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2 import constants, instructions
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.metavm import Generator as OOGenerator
from pypy.translator.oosupport.constant import push_constant
from collections import namedtuple

Scope = namedtuple("Scope", "block parent registers namespaces")

class Avm2ilasm(OOGenerator):
    """ AVM2 'assembler' generator routines """
    def __init__(self):
        self.scope = Scope(None, None, [], [constants.PRIVATE_NAMESPACE, constants.PACKAGE_NAMESPACE])
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

    def emit(self, instr, *args):
        self.I(instructions.INSTRUCTIONS[instr](*args))

    def load(self, v):
        if hasattr(v, "__iter__")  and not isinstance(v, basestring):
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
    
    def push_this(self):
        self.I(instructions.getlocal(0))

    def push_arg(self, v):
        assert v.name in self.registers
        self.push_local(v)
    
    def push_local(self, v):
        self.push_var(v.name)

    def push_var(self, v):
        assert v in self.registers
        self.I(instructions.getlocal(self.registers.find(v)))

    def push_const(self, v):
        if isinstance(v, int):
            if 0 < v < 256:
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
