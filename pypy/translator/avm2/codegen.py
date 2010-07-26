""" backend generator routines
"""

import re

from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2 import types_ as types
from pypy.translator.oosupport.metavm import Generator
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.constant import push_constant
from pypy.translator.oosupport.function import render_sub_op

from mech.fusion.avm2 import instructions, codegen
from mech.fusion.avm2.constants import MultinameL
from mech.fusion.avm2.interfaces import LoadableAdapter, IMultiname

from zope.interface import implementer
from zope.component import provideAdapter, adapter

@adapter(Variable)
class VariableLoadable(LoadableAdapter):
    def load(self, generator):
        v = self.value
        if v.concretetype is ootype.Void:
            generator.push_null()
        else:
            generator.push_local(v)

provideAdapter(VariableLoadable)

@adapter(Constant)
class ConstantLoadable(LoadableAdapter):
    def load(self, generator):
        v = self.value
        push_constant(generator.db, v.concretetype, v.value, generator)

provideAdapter(ConstantLoadable)

@adapter(SubOperation)
class SubOpLoadable(LoadableAdapter):
    def load(self, generator):
        render_sub_op(self.value, generator.db, generator)

provideAdapter(SubOpLoadable)

class PyPyCodeGenerator(codegen.CodeGenerator, Generator):
    def __init__(self, db, abc, optimize=False):
        super(PyPyCodeGenerator, self).__init__(abc, optimize=optimize)
        self.db  = db
        self.cts = db.genoo.TypeSystem(db)

    def _get_type(self, TYPE):
        t = self.cts.lltype_to_cts(TYPE)
        if t:
            return IMultiname(t)
        return super(PyPyCodeGenerator, self)._get_type(TYPE)

    def oonewarray(self, TYPE, length=1):
        super(PyPyCodeGenerator, self).new_vector(TYPE.ITEM, length)

    def store(self, v):
        """
        Pop a value off the stack and store it in the variable.
        """
        self.store_var(v.name)

    def push_local(self, v):
        """
        Get the local occupied to "name" and push it to the stack.
        """
        if self.HL(v.name):
            self.push_var(v.name)
        else:
            self.push_null()

    def push_primitive_constant(self, TYPE, value):
        if TYPE is ootype.Void:
            self.push_null()
        elif TYPE is ootype.String:
            if value._str is None:
                self.push_null()
                self.downcast(types.types.string)
            else:
                self.load(value._str)
        else:
            self.load(value)

    def call_graph(self, graph, args=[]):
        """
        Call a graph.
        """
        self.db.pending_function(graph)
        qname = self.cts.graph_to_qname(graph)
        self.emit('findpropstrict', qname)
        args = [a for a in args if a.concretetype is not ootype.Void]
        self.load(*args)
        self.emit('callproperty', qname, len(args))

    def new(self, TYPE):
        # XXX: assume no args for now
        self.load(self._get_type(TYPE))
        self.I(instructions.construct(0))

    def stringbuilder_ll_append(self, args):
        self.load(*args)
        self.I(instructions.add())
        self.store(args[0])
        self.push_null()

    stringbuilder_ll_append_char = stringbuilder_ll_append

    def list_ll_setitem_fast(self, args):
        list, index, value = args
        self.load(list)
        if isinstance(index, Constant):
            self.load(value)
            self.set_field(index.value)
        else:
            self.load(index)
            self.load(value)
            self.set_field(MultinameL())
        # XXX: oosend expects a value to send to StoreResult
        # We don't generate one, push a null.
        self.push_null()

    def list_ll_getitem_fast(self, args):
        list, index = args
        self.load(list)
        if isinstance(index, Constant):
            self.get_field(index.value, list.concretetype.ITEM)
        else:
            self.load(index)
            self.get_field(MultinameL(), list.concretetype.ITEM)
