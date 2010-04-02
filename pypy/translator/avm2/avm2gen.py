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
from pypy.translator.oosupport.function import render_sub_op

from itertools import chain

class PyPyAvm2ilasm(avm2gen.Avm2ilasm, Generator):
    def __init__(self, db, abc, optimize=False):
        super(PyPyAvm2ilasm, self).__init__(abc, optimize=optimize)
        self.db  = db
        self.cts = db.genoo.TypeSystem(db)

    def _get_type(self, TYPE):
        t = self.cts.lltype_to_cts(TYPE)
        if t:
            return t.multiname()
        return super(PyPyAvm2ilasm, self)._get_type(TYPE)

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
        else:
            super(PyPyAvm2ilasm, self).load(v)

        for e in args:
            self.load(e)

    def oonewarray(self, TYPE, length=1):
        self.load(types.vec_qname)
        self.load(self.cts.lltype_to_cts(TYPE.ITEM))
        self.I(instructions.applytype(1))
        self.load(length)
        self.I(instructions.construct(1))
        self.I(instructions.coerce(self.cts.lltype_to_cts(TYPE)))

    def push_primitive_constant(self, TYPE, value):
        if TYPE is ootype.Void:
            self.push_null()
        elif TYPE is ootype.String:
            if value._str is None:
                self.push_null()
                self.downcast(types.types.string)
            else:
                self.push_const(value._str)
        else:
            self.push_const(value)

    def new(self, TYPE):
        # XXX: assume no args for now
        t = self._get_type(TYPE)
        self.emit('findpropstrict', t)
        self.emit('constructprop', t, 0)

    def array_setitem(self):
        self.I(instructions.setproperty(constants.MultinameL(
                    constants.PROP_NAMESPACE_SET)))
        # XXX: oosend expects a value to send to StoreResult
        # We don't generate one, push a null.
        self.push_null()

    def array_getitem(self):
        self.I(instructions.getproperty(constants.MultinameL(
                    constants.PROP_NAMESPACE_SET)))

    def call_graph(self, graph, args=[]):
        """
        Call a graph.
        """
        self.db.pending_function(graph)
        namespace = getattr(graph.func, '_namespace_', None)
        numargs = len(args)
        if namespace:
            qname = constants.packagedQName(namespace, graph.name)
        else:
            qname = constants.QName(graph.name)
        self.emit('findpropstrict', qname)
        self.load(*args)
        self.emit('callproperty', qname, numargs)

    def store(self, v):
        """
        Pop a value off the stack and store it in the variable.
        """
        self.store_var(v.name)

    def push_local(self, v):
        """
        Get the local occupied to "name" and push it to the stack.
        """
        self.push_var(v.name)

    push_arg = push_local
