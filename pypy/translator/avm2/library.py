
import functools

from pypy.rpython.ootypesystem import ootype

from mech.fusion.avm2            import playerglobal
from mech.fusion.avm2.interfaces import IMultiname
from mech.fusion.avm2.constants  import QName, TypeName, undefined
from mech.fusion.avm2.library    import make_package

from pypy.translator.avm2.runtime import AVM2Class, AVM2Instance, _static_meth

def ClassDescConverter(classdesc, _cache={}):
    T = classdesc.Library.get_type
    C = lambda t: ClassDescConverter(t)._INSTANCE
    def resolve(TYPE):
        if TYPE in classdesc.Library:
            return C(T(TYPE))

        if type(TYPE) == object or TYPE in (undefined, None): # interfaces and root objects
            return ootype.ROOT
        name = IMultiname(TYPE)

        if isinstance(name, TypeName):
            return C(T(name.name).specialize(name.types))

        return name

    def create_methods(methods, meth, Meth):
        return dict((name, meth(Meth([resolve(arg) for arg in args], resolve(result))))
                    for name, args, result in methods)

    if classdesc in _cache:
        return _cache[classdesc]

    TYPE = AVM2Instance(classdesc.Package, classdesc.ShortName, None)
    Class = AVM2Class(TYPE, {}, {})
    _cache[classdesc] = Class

    if classdesc.FullName == QName('Object'):
        TYPE._set_superclass(ootype.ROOT)
    else:
        TYPE._set_superclass(resolve(classdesc.BaseType))

    # add both static and instance methods, and static fields
    static_meths = create_methods(classdesc.StaticMethods, _static_meth, ootype.StaticMethod)
    meths = create_methods(classdesc.Methods, ootype.meth, ootype.Meth)
    Class._add_methods(static_meths)
    Class._add_static_fields(dict((t[0], resolve(t[1])) for t in
        classdesc.StaticFields + classdesc.StaticProperties))

    TYPE._add_methods(meths)
    TYPE._add_fields(dict((t[0], resolve(t[1])) for t in
        classdesc.Fields + classdesc.Properties if not TYPE._has_field(t[0])))

    return Class

convert_package = functools.partial(make_package, Interface=ClassDescConverter)
get_playerglobal = functools.partial(make_package, playerglobal, ClassDescConverter)
