import types
from pypy.objspace.flow.model import FunctionGraph
from pypy.interpreter.pycode import cpython_code_signature
from pypy.interpreter.argument import ArgErr


class CallFamily:
    """A family of Desc objects that could be called from common call sites.
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

    def pycall(self, schedule, args):
        inputcells = self.parse_arguments(args)
        result = self.specialize(inputcells)
        if isinstance(result, FunctionGraph):
            graph = result         # common case
            result = schedule(graph, inputcells)
        return result

    def bind(self, classdef):
        # XXX static methods
        return self.bookkeeper.getmethoddesc(self, classdef)


class ClassDesc(Desc):
    knowntype = type

    def __init__(self, bookkeeper, pyobj, specialize=None):
        super(ClassDesc, self).__init__(bookkeeper, pyobj)
        self.name = pyobj.__module__ + '.' + pyobj.__name__
        if specialize is None:
            tag = pyobj.__dict__.get('_annspecialcase_', '')
            assert not tag  # XXX later
        self.specialize = specialize
        self._classdef = None

    def getuniqueclassdef(self):
        if self.specialize:
            raise Exception("not supported on class %r because it needs "
                            "specialization" % (self.name,))
        if self._classdef is None:
            from pypy.annotation.classdef import ClassDef
            classdef = ClassDef(self.pyobj, self.bookkeeper)
            self.bookkeeper.classdefs.append(classdef)
            self._classdef = classdef
            classdef.setup()
        return self._classdef

    def pycall(self, schedule, args):
        from pypy.annotation.model import SomeInstance
        classdef = self.getuniqueclassdef()
        s_instance = SomeInstance(classdef)
        init = getattr(self.pyobj, '__init__', None)  # xxx
        if init is not None and init != object.__init__:
            # call the constructor
            s_init = self.bookkeeper.immutablevalue(init)
            args = args.prepend(s_instance)
            s_init.call(args)
        else:
            try:
                args.fixedunpack(0)
            except ValueError:
                raise Exception("default __init__ takes no argument"
                                " (class %s)" % (self.name,))
        return s_instance


class MethodDesc(Desc):
    knowntype = types.MethodType

    def __init__(self, bookkeeper, funcdesc, classdef):
        super(MethodDesc, self).__init__(bookkeeper)
        self.funcdesc = funcdesc
        self.classdef = classdef

    def __repr__(self):
        return '<MethodDesc %r of %r>' % (self.funcdesc,
                                          self.classdef)

    def pycall(self, schedule, args):
        from pypy.annotation.model import SomeInstance
        s_instance = SomeInstance(self.classdef)
        args = args.prepend(s_instance)
        return self.funcdesc.pycall(schedule, args)

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
