import types
from pypy.objspace.flow.model import Constant, FunctionGraph
from pypy.interpreter.pycode import cpython_code_signature
from pypy.interpreter.argument import ArgErr


class CallFamily:
    """A family of Desc objects that could be called from common call sites.
    The call families are conceptually a partition of all (callable) Desc
    objects, where the equivalence relation is the transitive closure of
    'd1~d2 if d1 and d2 might be called at the same call site'.
    """
    def __init__(self, desc):
        self.descs = { desc: True }
        self.patterns = {}    # set of "call shapes" in the sense of
                              # pypy.interpreter.argument.Argument

    def update(self, other):
        self.descs.update(other.descs)
        self.patterns.update(other.patterns)

class AttrFamily:
    """A family of Desc objects that have common 'getattr' sites.
    The attr families are conceptually a partition of FrozenDesc and ClassDesc
    objects, where the equivalence relation is the transitive closure of
    'd1~d2 if d1 and d2 might have an attribute read on them by the same
    getattr operation.'
    """
    def __init__(self, desc):
        self.descs = { desc: True }
        self.read_locations = {}     # set of position_keys
        self.attrs = {}              # { attr: s_value }

    def update(self, other):
        self.descs.update(other.descs)
        self.read_locations.update(other.read_locations)
        self.attrs.update(other.attrs)

# ____________________________________________________________

class Desc(object):
    def __init__(self, bookkeeper, pyobj=None):
        self.bookkeeper = bookkeeper
        # 'pyobj' is non-None if there is an associated underlying Python obj
        self.pyobj = pyobj

    def __repr__(self):
        pyobj = self.pyobj
        if pyobj is None:
            return object.__repr__(self)
        return '<%s for %r>' % (self.__class__.__name__, pyobj)

    def getcallfamily(self):
        """Get the CallFamily object."""
        call_families = self.bookkeeper.pbc_maximal_call_families
        _, _, callfamily = call_families.find(self)
        return callfamily

    def mergecallfamilies(self, *others):
        """Merge the call families of the given Descs into one."""
        call_families = self.bookkeeper.pbc_maximal_call_families
        changed, rep, callfamily = call_families.find(self)
        for desc in others:
            changed1, rep, callfamily = call_families.union(rep, desc)
            changed = changed or changed1
        return changed

    def getattrfamily(self):
        """Get the AttrFamily object."""
        access_sets = self.bookkeeper.pbc_maximal_access_sets
        _, _, attrfamily = access_sets.find(self)
        return attrfamily

    def mergeattrfamilies(self, *others):
        """Merge the attr families of the given Descs into one."""
        access_sets = self.bookkeeper.pbc_maximal_access_sets
        changed, rep, attrfamily = access_sets.find(self)
        for desc in others:
            changed1, rep, attrfamily = access_sets.union(rep, desc)
            changed = changed or changed1
        return changed

    def bind(self, classdef):
        return self


class FunctionDesc(Desc):
    knowntype = types.FunctionType
    
    def __init__(self, bookkeeper, pyobj=None,
                 name=None, signature=None, defaults=None,
                 specializer=None):
        super(FunctionDesc, self).__init__(bookkeeper, pyobj)
        if name is None:
            name = pyobj.func_name
        if signature is None:
            signature = cpython_code_signature(pyobj.func_code)
        if defaults is None:
            defaults = pyobj.func_defaults
        if specializer is None:
            tag = getattr(pyobj, '_annspecialcase_', None)
            policy = bookkeeper.annotator.policy
            specializer = policy.get_specializer(tag)
        self.name = name
        self.signature = signature
        self.defaults = defaults or ()
        # 'specializer' is a function with the following signature:
        #      specializer(funcdesc, args_s) => graph
        #                                 or => s_result (overridden/memo cases)
        self.specializer = specializer
        self._cache = {}     # convenience for the specializer

    def buildgraph(self):
        translator = self.bookkeeper.annotator.translator
        return translator.buildflowgraph(self.pyobj)

    def cachedgraph(self, key):
        try:
            return self._cache[key]
        except KeyError:
            graph = self.buildgraph()
            self._cache[key] = graph
            return graph

    def parse_arguments(self, args):
        defs_s = []
        for x in self.defaults:
            defs_s.append(self.bookkeeper.immutablevalue(x))
        try:
            inputcells = args.match_signature(self.signature, defs_s)
        except ArgErr, e:
            raise TypeError, "signature mismatch: %s" % e.getmsg(args, self.name)
        return inputcells

    def specialize(self, inputcells):
        return self.specializer(self, inputcells)

    def pycall(self, schedule, args, s_previous_result):
        inputcells = self.parse_arguments(args)
        result = self.specialize(inputcells)
        if isinstance(result, FunctionGraph):
            graph = result         # common case
            result = schedule(graph, inputcells)
        # Some specializations may break the invariant of returning
        # annotations that are always more general than the previous time.
        # We restore it here:
        from pypy.annotation.model import unionof
        result = unionof(result, s_previous_result)
        return result

    def bind(self, classdef):
        # XXX static methods
        return self.bookkeeper.getmethoddesc(self, classdef)


class ClassDesc(Desc):
    knowntype = type
    instance_level = False

    def __init__(self, bookkeeper, pyobj=None,
                 name=None, basedesc=None, classdict=None,
                 specialize=None):
        super(ClassDesc, self).__init__(bookkeeper, pyobj)

        if name is None:
            name = pyobj.__module__ + '.' + pyobj.__name__
        self.name = name
        self.basedesc = basedesc
        if classdict is None:
            classdict = {}    # populated below
        self.classdict = classdict     # {attr: Constant-or-Desc}
        if specialize is None:
            specialize = pyobj.__dict__.get('_annspecialcase_', '')
        self.specialize = specialize
        self._classdefs = {}

        if pyobj is not None:
            cls = pyobj
            base = object
            baselist = list(cls.__bases__)
            baselist.reverse()

            for b1 in baselist:
                if b1 is object:
                    continue
                if getattr(b1, '_mixin_', False):
                    assert b1.__bases__ == () or b1.__bases__ == (object,), (
                        "mixin class %r should have no base" % (b1,))
                    self.add_sources_for_class(b1)
                else:
                    assert base is object, ("multiple inheritance only supported "
                                            "with _mixin_: %r" % (cls,))
                    base = b1

            self.add_sources_for_class(cls)
            if base is not object:
                self.basedesc = bookkeeper.getdesc(base)

    def add_sources_for_class(self, cls):
        for name, value in cls.__dict__.items():
            ## -- useless? -- ignore some special attributes
            ##if name.startswith('_') and not isinstance(value, types.FunctionType):
            ##    continue
            if isinstance(value, types.FunctionType):
                # for debugging
                if not hasattr(value, 'class_'):
                    value.class_ = self.pyobj # remember that this is really a method
                if self.specialize:
                    # make a custom funcdesc that specializes on its first
                    # argument (i.e. 'self').
                    from pypy.annotation.specialize import argtype
                    funcdesc = FunctionDesc(self.bookkeeper, value,
                                            specializer=argtype(0))
                    self.classdict[name] = funcdesc
                    continue
                # NB. if value is, say, AssertionError.__init__, then we
                # should not use getdesc() on it.  Never.  The problem is
                # that the py lib has its own AssertionError.__init__ which
                # is of type FunctionType.  But bookkeeper.immutablevalue()
                # will do the right thing in s_get_value().
            self.classdict[name] = Constant(value)

    def getclassdef(self, key):
        try:
            return self._classdefs[key]
        except KeyError:
            from pypy.annotation.classdef import ClassDef, FORCE_ATTRIBUTES_INTO_CLASSES
            classdef = ClassDef(self.bookkeeper, self)
            self.bookkeeper.classdefs.append(classdef)
            self._classdefs[key] = classdef

            # forced attributes
            if self.pyobj is not None:
                cls = self.pyobj
                if cls in FORCE_ATTRIBUTES_INTO_CLASSES:
                    for name, s_value in FORCE_ATTRIBUTES_INTO_CLASSES[cls].items():
                        classdef.generalize_attr(name, s_value)
                        classdef.find_attribute(name).readonly = False

            # register all class attributes as coming from this ClassDesc
            # (as opposed to prebuilt instances)
            classsources = {}
            for attr in self.classdict:
                classsources[attr] = self    # comes from this ClassDesc
            classdef.setup(classsources)
            return classdef

    def getuniqueclassdef(self):
        if self.specialize:
            raise Exception("not supported on class %r because it needs "
                            "specialization" % (self.name,))
        return self.getclassdef(None)

    def pycall(self, schedule, args, s_previous_result):
        from pypy.annotation.model import SomeInstance, SomeImpossibleValue
        if self.specialize:
            if self.specialize == 'specialize:ctr_location':
                # We use the SomeInstance annotation returned the last time
                # to make sure we use the same ClassDef this time.
                if isinstance(s_previous_result, SomeInstance):
                    classdef = s_previous_result.classdef
                else:
                    classdef = self.getclassdef(object())
            else:
                raise Exception("unsupported specialization tag: %r" % (
                    self.specialize,))
        else:
            classdef = self.getuniqueclassdef()
        s_instance = SomeInstance(classdef)
        # look up __init__ directly on the class, bypassing the normal
        # lookup mechanisms ClassDef (to avoid influencing Attribute placement)
        s_init = self.s_read_attribute('__init__')
        if isinstance(s_init, SomeImpossibleValue):
            # no __init__: check that there are no constructor args
            try:
                args.fixedunpack(0)
            except ValueError:
                raise Exception("default __init__ takes no argument"
                                " (class %s)" % (self.name,))
        else:
            # call the constructor
            args = args.prepend(s_instance)
            s_init.call(args)
        return s_instance

    def s_read_attribute(self, name):
        # look up an attribute in the class
        cdesc = self
        while name not in cdesc.classdict:
            cdesc = cdesc.basedesc
            if cdesc is None:
                from pypy.annotation.model import s_ImpossibleValue
                return s_ImpossibleValue
        else:
            # delegate to s_get_value to turn it into an annotation
            return cdesc.s_get_value(None, name)

    def s_get_value(self, classdef, name):
        obj = self.classdict[name]
        if isinstance(obj, Constant):
            s_value = self.bookkeeper.immutablevalue(obj.value)
            if classdef is not None:
                s_value = s_value.bindcallables(classdef)
        elif isinstance(obj, Desc):
            from pypy.annotation.model import SomePBC
            if classdef is not None:
                obj = obj.bind(classdef)
            s_value = SomePBC([obj])
        else:
            raise TypeError("classdict should not contain %r" % (obj,))
        return s_value

    def find_source_for(self, name):
        if name in self.classdict:
            return self
        if self.pyobj is not None:
            # check whether in the case the classdesc corresponds to a real class
            # there is a new attribute
            cls = self.pyobj
            if name in cls.__dict__:
                self.classdict[name] = Constant(cls.__dict__[name])
                return self
        return None


class MethodDesc(Desc):
    knowntype = types.MethodType

    def __init__(self, bookkeeper, funcdesc, classdef):
        super(MethodDesc, self).__init__(bookkeeper)
        self.funcdesc = funcdesc
        self.classdef = classdef

    def __repr__(self):
        return '<MethodDesc %r of %r>' % (self.funcdesc,
                                          self.classdef)

    def pycall(self, schedule, args, s_previous_result):
        from pypy.annotation.model import SomeInstance
        s_instance = SomeInstance(self.classdef)
        args = args.prepend(s_instance)
        return self.funcdesc.pycall(schedule, args, s_previous_result)

    def bind(self, classdef):
        self.bookkeeper.warning("rebinding an already bound %r" % (self,))
        return self.funcdesc.bind(classdef)


def new_or_old_class(c):
    if hasattr(c, '__class__'):
        return c.__class__
    else:
        return type(c)

class FrozenDesc(Desc):

    def __init__(self, bookkeeper, pyobj):
        super(FrozenDesc, self).__init__(bookkeeper, pyobj)
        self.attributes = self.pyobj.__dict__.copy()
        self.knowntype = new_or_old_class(pyobj)
        assert bool(pyobj), "__nonzero__ unsupported on frozen PBC %r" %(pyobj,)

    def s_read_attribute(self, attr):
        if attr in self.attributes:
            return self.bookkeeper.immutablevalue(self.attributes[attr])
        else:
            from pypy.annotation.model import s_ImpossibleValue
            return s_ImpossibleValue


class MethodOfFrozenDesc(Desc):
    knowntype = types.MethodType

    def __init__(self, bookkeeper, funcdesc, frozendesc):
        super(MethodOfFrozenDesc, self).__init__(bookkeeper)
        self.funcdesc = funcdesc
        self.frozendesc = frozendesc

    def __repr__(self):
        return '<MethodOfFrozenDesc %r of %r>' % (self.funcdesc,
                                                  self.frozendesc)

    def pycall(self, schedule, args, s_previous_result):
        from pypy.annotation.model import SomePBC
        s_self = SomePBC([self.frozendesc])
        args = args.prepend(s_self)
        return self.funcdesc.pycall(schedule, args, s_previous_result)
