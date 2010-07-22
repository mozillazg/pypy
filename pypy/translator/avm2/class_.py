
from py.builtin import set

from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2.node import ClassNodeBase
from pypy.translator.avm2.types_ import types
from pypy.translator.oosupport.constant import push_constant

from mech.fusion.avm2.constants import QName, packagedQName
from mech.fusion.avm2.interfaces import IMultiname

class Class(ClassNodeBase):
    def __init__(self, db, INSTANCE, namespace, name):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.INSTANCE = INSTANCE
        print INSTANCE, INSTANCE._superclass
        self.exception = ootype.isSubclass(self.INSTANCE, self.db.genoo.EXCEPTION)
        self.namespace = namespace
        self.name = name

    def __hash__(self):
        return hash(self.INSTANCE)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.INSTANCE == other.INSTANCE

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '<Class %s>' % self.name

    def dependencies(self):
        if self.INSTANCE._superclass._superclass:
            self.db.pending_class(self.INSTANCE._superclass)

    def get_fields(self):
        return self.INSTANCE._fields.iteritems()

    def get_name(self):
        return self.name

    def get_full_name(self):
        if self.namespace is None:
            return self.name
        else:
            return '%s::%s' % (self.namespace, self.name)

    def get_type(self):
        return packagedQName(self.namespace, self.name)

    def get_base_class(self):
        base_class = self.INSTANCE._superclass
        if self.INSTANCE is self.db.genoo.EXCEPTION:
            return QName("Error")
        elif self.INSTANCE._superclass._superclass:
            ns, name = self.db.class_name(base_class).rsplit('::', 1)
            return packagedQName(ns, name)
        return QName("Object")

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

    def render_ctor(self, ilasm):
        ilasm.begin_constructor()
        # set default values for fields
        default_values = self.INSTANCE._fields.copy()
        default_values.update(self.INSTANCE._overridden_defaults)
        for f_name, (F_TYPE, f_default) in default_values.iteritems():
            if getattr(F_TYPE, '_is_value_type', False):
                continue # we can't set it to null
            # INSTANCE_DEF, _ = self.INSTANCE._lookup_field(f_name)
            cts_type = self.cts.lltype_to_cts(F_TYPE)
            f_name = self.cts.escape_name(f_name)
            if cts_type != types.void:
                ilasm.push_this()
                push_constant(self.db, F_TYPE, f_default, ilasm)
                # class_name = self.db.class_name(INSTANCE_DEF)
                ilasm.set_field(f_name)
        ilasm.end_constructor()

    def render_methods(self, ilasm):
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
                ilasm.emit('findpropstrict', QName("Error"))
                ilasm.load("Abstract method %s::%s called" % (self.name, m_name))
                ilasm.emit('constructprop', QName("Error"), 1)
                ilasm.throw()
                ilasm.exit_context()

        self.render_getName(ilasm)

    def render_toString(self, ilasm):
        override = self.INSTANCE._superclass._superclass is not None
        wrapper = "Exception" if self.exception else "Instance"
        ilasm.begin_method('toString', [], types.string, override=override)
        ilasm.load("%sWrapper('%s')" % (wrapper, self.name))
        ilasm.return_value()
        ilasm.end_method()

    def render_getName(self, ilasm):
        override = self.INSTANCE._superclass._superclass is not None
        ilasm.begin_method('getName', [], types.string, override=override)
        ilasm.load(self.name)
        ilasm.return_value()
        ilasm.end_method()
