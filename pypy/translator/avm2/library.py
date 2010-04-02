
from pypy.rpython.ootypesystem import ootype

from mech.fusion.avm2.constants import QName, packagedQName, TYPE_MULTINAME_TypeName
from mech.fusion.avm2.query import ClassDesc
from mech.fusion.avm2.library import Library
from mech.fusion.avm2.playerglobal.flash.utils import Vector

from pypy.translator.avm2.types_ import vec_qname

## Monkey Patching!

ClassDesc._nativeclass = None

class PyPyLibrary(Library):
    def resolve_class(self, TYPE):
        if self.has_type(TYPE):
            return self.get_type(TYPE)
        if playerglobal_lib.has_type(TYPE):
            return self.get_type(TYPE)
        if TYPE.KIND == TYPE_MULTINAME_TypeName and TYPE.name == vec_qname:
            assert len(TYPE.types) == 1
            return Vector[TYPE.types[0]]
        if getattr(TYPE, "multiname", None):
            return TYPE.multiname()

    def convert_classdesc(self, classdesc):
        resolve = self.resolve_class
        from pypy.translator.avm2.runtime import NativeClass, NativeInstance
        from pypy.translator.avm2.runtime import _overloaded_static_meth, _static_meth

        if classdesc._nativeclass is not None:
            return classdesc._nativeclass

        TYPE = NativeInstance(classdesc.Package, classdesc.ShortName, None, {}, {})
        Class = NativeClass(TYPE, {}, {})
        classdesc._nativeclass = Class
        if classdesc.FullName == QName('Object'):
            TYPE._set_superclass(ootype.ROOT)
        else:
            BASETYPE = resolve(classdesc.BaseType)
            TYPE._set_superclass(BASETYPE)

        TYPE._isArray = classdesc.IsArray
        if classdesc.IsArray:
            TYPE._ELEMENT = resolve(classdesc.ElementType)

        # add both static and instance methods, and static fields
        static_meths = self.group_methods(classdesc.StaticMethods,
            _overloaded_static_meth, _static_meth, ootype.StaticMethod)
        meths = self.group_methods(classdesc.Methods, ootype.overload,
                              ootype.meth, ootype.Meth)
        Class._add_methods(static_meths)
        Class._add_static_fields(dict((name,
            resolve(t)) for name, t in classdesc.StaticFields]))
        Class._add_static_fields(dict((name,
            resolve(t)) for name, t, g, s in classdesc.StaticProperties))
        TYPE._add_methods(meths)
        TYPE._add_fields(dict((name, resolve(t)) for name, t in classdesc.Fields))
        TYPE._add_fields(dict((name, resolve(t)) for name, t, g, s in classdesc.Properties))
        return Class

    def group_methods(self, methods, overload, meth, Meth):
        from pypy.translator.avm2.runtime import OverloadingResolver
        groups = {}
        for name, args, result, AS3 in methods:
            groups[name] = args, result, AS3

        res = {}
        attrs = dict(resolver=OverloadingResolver)
        for name, methlist in groups.iteritems():
            meths = [meth(Meth([self.resolve_class(arg) for arg in args],
                          self.resolve_class(result))) for (args, result) in methlist]
            res[name] = overload(*meths, **attrs)
        return res

from mech.fusion.avm2.library import get_playerglobal

playerglobal_lib = get_playerglobal(Library=PyPyLibrary)
playerglobal_lib.install_global(__name__.rpartition(".")[0]+".playerglobal")
