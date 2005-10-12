
"""typesystem.py -- Typesystem-specific operations for RTyper."""

from pypy.annotation.pairtype import extendabletype

from pypy.rpython.ootype import ootype
from pypy.rpython import lltype # FIXME lltype in separate directory

class TypeSystem(object):
    __metaclass__ = extendabletype

    def deref(self, obj):
        """Dereference `obj' to concrete object."""
        raise NotImplementedError()

    def getcallable(self, translator, graphfunc, getconcretetype=None):
        """Return callable given a Python function."""
        if getconcretetype is None:
            getconcretetype = self.getconcretetype
        graph = translator.getflowgraph(graphfunc)
        llinputs = [getconcretetype(v) for v in graph.getargs()]
        lloutput = getconcretetype(graph.getreturnvar())

        typ, constr = self.callable_trait
        
        FT = typ(llinputs, lloutput)
        _callable = getattr(graphfunc, '_specializedversionof_', graphfunc)
        return constr(FT, graphfunc.func_name, graph = graph, _callable = _callable)

    def getconcretetype(self, v):
        """Helper called by getcallable() to get the conrete type of a variable
in a graph."""
        raise NotImplementedError()

class LowLevelTypeSystem(TypeSystem):
    callable_trait = (lltype.FuncType, lltype.functionptr)

    def deref(self, obj):
        assert isinstance(lltype.typeOf(obj), lltype.Ptr)
        return obj._obj

    def getconcretetype(self, v):
        return getattr(v, 'concretetype', lltype.Ptr(lltype.PyObject))

class ObjectOrientedTypeSystem(TypeSystem):
    callable_trait = (ootype.StaticMethod, ootype.static_meth)

    def deref(self, obj):
        assert isinstance(ootype.typeOf(obj), ootype.OOType)
        return obj

# All typesystems are singletons
LowLevelTypeSystem.instance = LowLevelTypeSystem()
ObjectOrientedTypeSystem.instance = ObjectOrientedTypeSystem()
