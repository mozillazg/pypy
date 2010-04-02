from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.node import Node
from pypy.translator.oosupport.constant import push_constant

from mech.fusion.avm2 import constants, traits
from pypy.translator.avm2 import types_ as types

try:
    set
except NameError:
    from sets import Set as set

class Class(Node):
    def __init__(self, db, INSTANCE, namespace, name):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.INSTANCE = INSTANCE
        self.exception = ootype.isSubclass(self.INSTANCE, self.db.genoo.EXCEPTION)
        self.namespace = namespace
        self.name = name

    def dependencies(self):
        if not self.is_root(self.INSTANCE):
            self.db.pending_class(self.INSTANCE._superclass)

    def __hash__(self):
        return hash(self.INSTANCE)

    def __eq__(self, other):
        return self.INSTANCE == other.INSTANCE

    def __ne__(self, other):
        return not self == other

    def is_root(INSTANCE):
        return INSTANCE._superclass is None
    is_root = staticmethod(is_root)

    def get_name(self):
        return self.name

    def __repr__(self):
        return '<Class %s>' % self.name

    def get_base_class(self):
        base_class = self.INSTANCE._superclass
        if self.INSTANCE is self.db.genoo.EXCEPTION:
            return constants.QName("Error")
        if self.is_root(base_class):
            return constants.QName("Object")
        else:
            ns, name = self.db.class_name(base_class).rsplit('::', 1)
            return constants.packagedQName(ns, name)

    def is_abstract(self):
        return False # XXX
        
        # if INSTANCE has an abstract method, the class is abstract
        method_names = set()
        for m_name, m_meth in self.INSTANCE._methods.iteritems():
            if not hasattr(m_meth, 'graph'):
                return True
            method_names.add(m_name)

        # if superclasses have abstract methods not overriden by
        # INSTANCE, the class is abstract
        abstract_method_names = set()
        cls = self.INSTANCE._superclass
        while cls is not None:
            abstract_method_names.update(cls._methods.keys())
            cls = cls._superclass
        not_overriden = abstract_method_names.difference(method_names)
        if not_overriden:
            return True
        
        return False

    def render(self, ilasm):        
        if self.is_root(self.INSTANCE):
            return

        self.ilasm = ilasm

        ilasm.begin_class(constants.packagedQName(self.namespace, self.name), self.get_base_class())
        for f_name, (f_type, f_default) in self.INSTANCE._fields.iteritems():
            cts_type = self.cts.lltype_to_cts(f_type)
            f_name = self.cts.escape_name(f_name)
            if cts_type != types.types.void:
                ilasm.context.add_instance_trait(traits.AbcSlotTrait(constants.QName(f_name), cts_type.multiname()))

        self._ctor()
        self._toString()

        for m_name, m_meth in self.INSTANCE._methods.iteritems():
            if hasattr(m_meth, 'graph'):
                # if the first argument's type is not a supertype of
                # this class it means that this method this method is
                # not really used by the class: don't render it, else
                # there would be a type mismatch.
                args =  m_meth.graph.getargs()
                SELF = args[0].concretetype
                if not ootype.isSubclass(self.INSTANCE, SELF):
                    continue
                f = self.db.genoo.Function(self.db, m_meth.graph, m_name)
                
                context = self.INSTANCE._superclass
                while context:
                    if m_name in context._methods:
                        f.override = True
                        break
                    context = context._superclass

                f.render(ilasm)
            else:
                # abstract method
                METH = m_meth._TYPE
                arglist = [(self.cts.lltype_to_cts(ARG), 'v%d' % i)
                           for i, ARG in enumerate(METH.ARGS)
                           if ARG is not ootype.Void]
                returntype = self.cts.lltype_to_cts(METH.RESULT)
                ilasm.begin_method(m_name, arglist, returntype)
                ilasm.emit('findpropstrict', constants.QName("Error"))
                ilasm.push_const("Abstract method %s::%s called" % (self.name, m_name))
                ilasm.emit('constructprop', constants.QName("Error"), 1)
                ilasm.throw()
                ilasm.exit_context()

        ilasm.exit_context()
    
    def _ctor(self):
        self.ilasm.begin_constructor()
        # set default values for fields
        default_values = self.INSTANCE._fields.copy()
        default_values.update(self.INSTANCE._overridden_defaults)
        for f_name, (F_TYPE, f_default) in default_values.iteritems():
            if getattr(F_TYPE, '_is_value_type', False):
                continue # we can't set it to null
            # INSTANCE_DEF, _ = self.INSTANCE._lookup_field(f_name)
            cts_type = self.cts.lltype_to_cts(F_TYPE)
            f_name = self.cts.escape_name(f_name)
            if cts_type != types.types.void:
                self.ilasm.push_this()
                push_constant(self.db, F_TYPE, f_default, self.gen)
                # class_name = self.db.class_name(INSTANCE_DEF)
                self.ilasm.set_field(f_name)
        self.ilasm.end_constructor()

    def _toString(self):
        if self.is_root(self.INSTANCE._superclass):
            override = False
        else:
            override = True
        print self.exception
        wrapper = "Exception" if self.exception else "Instance"
        self.ilasm.begin_method('toString', [], types.types.string, override=override)
        self.ilasm.load("%sWrapper('%s')" % (wrapper, self.name))
        self.ilasm.return_value()
        self.ilasm.end_method()
