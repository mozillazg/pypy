import sys
import cPickle as pickle
import os.path
import py
import subprocess
from pypy.tool.udir import udir
from pypy.rpython.ootypesystem import ootype
from pypy.translator import avm2
from pypy.translator.cli.support import log

Types = {} # TypeName -> ClassDesc
Namespaces = set()

#_______________________________________________________________________________
# This is the public interface of query.py

def get_native_class(name):
    desc = get_class_desc(name)
    return desc.get_nativeclass()

#_______________________________________________________________________________

# def load_pypylib():
#     from pypy.translator.cli.rte import get_pypy_dll
#     dll = get_pypy_dll()
#     try:
#         import clr
#         from System.Reflection import Assembly
#     except ImportError:
#         pass
#     else:
#         ass = Assembly.LoadFrom(dll)
#         assert ass is not None
#         clr.AddReference(pypylib)
#     load_assembly(pypylib)

def load_playerglobal():
    _cache = get_cachedir()
    outfile = _cache.join('avm2_playerglobal.pickle')
    if outfile.check():
        f = outfile.open('rb')
        types = pickle.load(f)
        f.close()
    else:
        types = load_and_cache_playerglobal(outfile)

    for ttype in types:
        parts = ttype.split('.')
        ns = parts[0]
        Namespaces.add(ns)
        for part in parts[1:-1]:
            ns = '%s.%s' % (ns, part)
            Namespaces.add(ns)
    Types.update(types)


def get_cachedir():
    import pypy
    _cache = py.path.local(pypy.__file__).new(basename='_cache').ensure(dir=1)
    return _cache

def load_and_cache_playerglobal(outfile):
    mydict = {}
    pipe = subprocess.Popen([sys.executable, str(py.path.local(avm2.__file__).dirpath("intrinsic/intrgen.py"))], stdout=subprocess.PIPE)
    exec pipe.stdout in mydict
    types = mydict['types']
    f = outfile.open('wb')
    pickle.dump(types, f, pickle.HIGHEST_PROTOCOL)
    f.close()
    return types

def get_ootype(name):
    # a bit messy, but works
    if name.startswith('ootype.'):
        _, name = name.split('.')
        return getattr(ootype, name)
    else:
        avm2class = get_native_class(name)
        return avm2class._INSTANCE

def get_class_desc(name):
    if name in Types:
        return Types[name]
    
    if name.endswith('[]'): # it's an array
        itemname = name[:-2]
        itemdesc = get_class_desc(itemname)
        desc = ClassDesc()
        desc.FullName = name
        desc.AssemblyQualifiedName = name # XXX
        desc.BaseType = 'Object'
        desc.ElementType = itemdesc.FullName
        desc.IsArray = True
        desc.Methods = [
            ('get', ['ootype.Signed', ], itemdesc.FullName),
            ('set', ['ootype.Signed', itemdesc.FullName], 'ootype.Void')
            ]
    else:
        assert False, 'Unknown desc'

    Types[name] = desc
    return desc


class ClassDesc(object):

    # default values
    Fields = []
    StaticFields = []
    StaticMethods = []
    Methods = []
    IsValueType = False

    _nativeclass = None

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        raise TypeError

    def get_nativeclass(self):
        from pypy.translator.avm2.runtime import NativeClass, NativeInstance
        from pypy.translator.avm2.runtime import _overloaded_static_meth, _static_meth

        if self._nativeclass is not None:
            return self._nativeclass

        # if self.Assembly == mscorlib:
        #     assembly = '[mscorlib]'
        # elif self.Assembly in (pypylib, pypylib2):
        #     assembly = '[pypylib]'
        # else:
        #     assert False, 'TODO: support external assemblies'
        namespace, name = self.FullName.rsplit('.', 1)
        
        # construct OOTYPE and CliClass
        # no superclass for now, will add it later
        TYPE = NativeInstance(namespace, name, None, {}, {})
        TYPE._is_value_type = self.IsValueType
        # TYPE._assembly_qualified_name = self.AssemblyQualifiedName
        Class = NativeClass(TYPE, {}, {})
        self._nativeclass = Class
        if self.FullName == 'Object':
            TYPE._set_superclass(ootype.ROOT)
        else:
            BASETYPE = get_ootype(self.BaseType)
            TYPE._set_superclass(BASETYPE)

        TYPE._isArray = self.IsArray
        if self.IsArray:
            TYPE._ELEMENT = get_ootype(self.ElementType)

        # add both static and instance methods, and static fields
        static_meths = self.group_methods(self.StaticMethods, _overloaded_static_meth,
                                          _static_meth, ootype.StaticMethod)
        meths = self.group_methods(self.Methods, ootype.overload, ootype.meth, ootype.Meth)
        fields = dict([(name, get_ootype(t)) for name, t in self.StaticFields])
        Class._add_methods(static_meths)
        Class._add_static_fields(fields)
        TYPE._add_methods(meths)
        return Class

    def group_methods(self, methods, overload, meth, Meth):
        from pypy.translator.avm2.runtime import OverloadingResolver
        groups = {}
        for name, args, result, AS3 in methods:
            groups[name] = args, result, AS3

        res = {}
        attrs = dict(resolver=OverloadingResolver)
        for name, methlist in groups.iteritems():
            TYPES = [self.get_method_type(Meth, args, result) for (args, result) in methlist]
            meths = [meth(TYPE) for TYPE in TYPES]
            res[name] = overload(*meths, **attrs)
        return res

    def get_method_type(self, Meth, args, result):
        ARGS = [get_ootype(arg) for arg in args]
        RESULT = get_ootype(result)
        return Meth(ARGS, RESULT)

placeholder = object()
class NativeNamespace(object):
    def __init__(self, name):
        self._name = name
        self.__treebuilt = False

    def __fullname(self, name):
        if self._name is None:
            return name
        else:
            return '%s.%s' % (self._name, name)

    def _buildtree(self):
        assert self._name is None, '_buildtree can be called only on top-level Runtime, not on namespaces'
        from pypy.translator.cli.support import getattr_ex
        load_playerglobal()
        for fullname in sorted(list(Namespaces)):
            if '.' in fullname:
                parent, name = fullname.rsplit('.', 1)
                parent = getattr_ex(self, parent)
                setattr(parent, name, NativeNamespace(fullname))
            else:
                setattr(self, fullname, NativeNamespace(fullname))

        for fullname in Types.iterkeys():
            if '.' in fullname:
                parent, name = fullname.rsplit('.', 1)
                parent = getattr_ex(self, parent)
            else:
                parent = self
            setattr(parent, name, placeholder)
        self.Object # XXX hack

    def __getattribute__(self, attr):
        value = object.__getattribute__(self, attr)
        if value is placeholder:
            fullname = self.__fullname(attr)
            value = get_native_class(fullname)
            setattr(self, attr, value)
        return value
