
""" backend generator routines
"""

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.ootypesystem import ootype
#from pypy.translator.avm1 import types_ as types
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.metavm import Generator as OOGenerator, InstructionList
from pypy.translator.oosupport.constant import push_constant
from collections import namedtuple

from mech.fusion.avm1 import actions, types_ as types, avm1gen

ClassName = namedtuple("ClassName", "namespace classname")
Scope = namedtuple("Scope", "block parent callback islabel")

def render_sub_op(sub_op, db, generator):
    op = sub_op.op
    instr_list = db.genoo.opcodes.get(op.opname, None)
    assert instr_list is not None, 'Unknown opcode: %s ' % op
    assert isinstance(instr_list, InstructionList)
    # Don't do that, please
    #assert instr_list[-1] is StoreResult, "Cannot inline an operation that doesn't store the result"

    # record that we know about the type of result and args
    db.cts.lltype_to_cts(op.result.concretetype)
    for v in op.args:
        db.cts.lltype_to_cts(v.concretetype)

    instr_list = InstructionList(instr_list[:-1]) # leave the value on the stack if this is a sub-op
    instr_list.render(generator, op)
    # now the value is on the stack

class PyPyAVM1Gen(avm1gen.AVM1Gen, OOGenerator):
    """
    AVM1 'assembler' generator routines
    """
    
    def load(self, v, *args):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is ootype.Void:
                return # ignore it
            else:
                self.push_local(v)
        elif isinstance(v, flowmodel.Constant):
            push_constant(self.db, v.concretetype, v.value, self)
        elif isinstance(v, SubOperation):
            render_sub_op(v, self.db, self)
            
        super(PyPyAVM1Gen, self).load(v, *args)


    def new(self, TYPE):
        if isinstance(TYPE, ootype.List):
            self.oonewarray(None)
    
