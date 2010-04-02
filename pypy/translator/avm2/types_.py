"""
bTranslate between PyPy ootypesystem and .NET Common Type System
"""

import exceptions

from py.builtin import set
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli import oopspec
from pypy.translator.cli.option import getoption

from mech.fusion.avm2 import constants

from pypy.tool.ansi_print import ansi_log

vec_qname = constants.packagedQName("__AS3__.vec", "Vector")
str_qname = constants.QName("String")
arr_qname = constants.QName("Array")

class Avm2Type(object):
    def typename(self):
        raise NotImplementedError

    def load_default(self, asm):
        raise NotImplementedError

    def __str__(self):
        return str(self.multiname())

    def __hash__(self):
        return hash(self.multiname())

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.multiname() == other.multiname()

    def __ne__(self, other):
        return not self == other

class Avm2PrimitiveType(Avm2Type):
    def __init__(self, name, default):
        self.name, self.default = name, default

    def load_default(self, gen):
        gen.load(self.default)

    def typename(self):
        return self.name

    def multiname(self):
        return constants.QName(self.typename())

class Avm2NamespacedType(Avm2Type):
    nstype = constants.TYPE_NAMESPACE_PackageNamespace
    def __init__(self, name, namespace=''):
        if '::' in name and namespace == '':
            self.ns, self.name = name.rsplit('::', 1)
        else:
            self.name = name
            self.ns = namespace

    def typename(self):
        return "%s::%s" % (self.ns, self.name)

    def multiname(self):
        return constants.QName(self.name, constants.Namespace(self.nstype, self.ns))

class Avm2ArrayType(Avm2Type):
    def __init__(self, itemtype):
        self.ITEM = itemtype

    def load_default(self, gen):
        gen.oonewarray(self, 0)

    def __str__(self):
        return "%s.<%s>" % (vec_qname, constants.QName(self.ITEM))

    def multiname(self):
        return constants.TypeName(vec_qname, constants.QName(self.ITEM))

T = Avm2PrimitiveType
# N = Avm2NamespacedType
class types:
    void   =  T('void', constants.null)
    int    =  T('int', -1)
    uint   =  T('uint', 0)
    bool   =  T('Boolean', False)
    float  =  T('Number', float('nan'))
    string =  T('String', "")
    type   =  T('Class', constants.QName('Class'))
    object =  T('Object', {})
    list   =  Avm2ArrayType
    dict   =  T('Object', {})
#    sb     =  N('StringBuilder', 'pypy.lib')
del T

_lltype_to_cts = {
    ootype.Void: types.void,
    ootype.Signed: types.int,
    ootype.Unsigned: types.uint,
    ootype.SignedLongLong: types.float,
    ootype.UnsignedLongLong: types.float,
    ootype.Bool: types.bool,
    ootype.Float: types.float,
    ootype.Char: types.string,
    ootype.UniChar: types.string,
    ootype.Class: types.type,
    ootype.String: types.string,
#   ootype.StringBuilder: types.sb,
    ootype.Unicode: types.string,
#   ootype.UnicodeBuilder: types.sb,

    # maps generic types to their ordinal
    ootype.List.SELFTYPE_T: types.list,
    ootype.Dict.SELFTYPE_T: types.dict,
}

class Avm2TypeSystem(object):
    def __init__(self, db):
        self.db = db

    def lltype_to_cts(self, t):
        if isinstance(t, Avm2Type):
            return t
        elif t is ootype.ROOT:
            return types.object
        elif isinstance(t, lltype.Ptr) and isinstance(t.TO, lltype.OpaqueType):
            return types.object
        elif isinstance(t, ootype.Instance):
            NATIVE_INSTANCE = t._hints.get('NATIVE_INSTANCE', None)
            if NATIVE_INSTANCE:
                return Avm2NamespacedType(NATIVE_INSTANCE._name)
            else:
                name = self.db.pending_class(t)
                return Avm2NamespacedType(name)
        elif isinstance(t, ootype.Record):
            name = self.db.pending_record(t)
            return Avm2NamespacedType(name)
        elif isinstance(t, ootype.StaticMethod):
            delegate = self.db.record_delegate(t)
            return Avm2NamespacedType(delegate)
        elif isinstance(t, (ootype.Array, ootype.List)):
            item_type = self.lltype_to_cts(t.ITEM)
            return types.list(item_type)
        elif isinstance(t, ootype.Dict):
            key_type = self.lltype_to_cts(t._KEYTYPE)
            value_type = self.lltype_to_cts(t._VALUETYPE)
            return types.dict
        ## elif isinstance(t, ootype.DictItemsIterator):
        ##     key_type = self.lltype_to_cts(t._KEYTYPE)
        ##     value_type = self.lltype_to_cts(t._VALUETYPE)
            ## if key_type == types.void:
            ##     key_type = types.int32 # placeholder
            ## if value_type == types.void:
            ##     value_type = types.int32 # placeholder
            ## return types.dict_items_iterator.specialize(key_type, value_type)

        return _lltype_to_cts.get(t, None)

    def llvar_to_cts(self, var):
        return self.lltype_to_cts(var.concretetype), var.name

    def llconst_to_cts(self, const):
        return self.lltype_to_cts(const.concretetype), const.value

    def escape_name(self, name):
        return name

    def graph_to_qname(self, graph):
        func_name = graph.name
        namespace = getattr(graph, '_namespace_', None)
        if namespace:
            return constants.packagedQName(namespace, func_name)
        else:
            return constants.QName(func_name)

    # def ctor_name(self, t):
    #     return 'instance void %s::.ctor()' % self.lltype_to_cts(t)

    # def graph_to_signature(self, graph, is_method = False, func_name = None):
    #     ret_type, ret_var = self.llvar_to_cts(graph.getreturnvar())
    #     func_name = func_name or graph.name
    #     func_name = self.escape_name(func_name)
    #     namespace = getattr(graph.func, '_namespace_', None)
    #     if namespace:
    #         func_name = '%s::%s' % (namespace, func_name)

    #     args = [arg for arg in graph.getargs() if arg.concretetype is not ootype.Void]
    #     if is_method:
    #         args = args[1:]

    #     arg_types = [self.lltype_to_cts(arg.concretetype).typename() for arg in args]
    #     arg_list = ', '.join(arg_types)

    #     return '%s %s(%s)' % (ret_type, func_name, arg_list)

    # def op_to_signature(self, op, func_name):
    #     ret_type, ret_var = self.llvar_to_cts(op.result)
    #     func_name = self.escape_name(func_name)

    #     args = [arg for arg in op.args[1:]
    #                 if arg.concretetype is not ootype.Void]

    #     arg_types = [self.lltype_to_cts(arg.concretetype).typename() for arg in args]
    #     arg_list = ', '.join(arg_types)

    #     return '%s %s(%s)' % (ret_type, func_name, arg_list)


    # def method_signature(self, TYPE, name_or_desc):
    #     # TODO: use callvirt only when strictly necessary
    #     if isinstance(TYPE, ootype.Instance):
    #         if isinstance(name_or_desc, ootype._overloaded_meth_desc):
    #             name = name_or_desc.name
    #             METH = name_or_desc.TYPE
    #             virtual = True
    #         else:
    #             name = name_or_desc
    #             owner, meth = TYPE._lookup(name)
    #             METH = meth._TYPE
    #             virtual = getattr(meth, '_virtual', True)
    #         class_name = self.db.class_name(TYPE)
    #         full_name = 'class %s::%s' % (class_name, self.escape_name(name))
    #         returntype = self.lltype_to_cts(METH.RESULT)
    #         arg_types = [self.lltype_to_cts(ARG).typename() for ARG in METH.ARGS if ARG is not ootype.Void]
    #         arg_list = ', '.join(arg_types)
    #         return '%s %s(%s)' % (returntype, full_name, arg_list), virtual

    #     elif isinstance(TYPE, (ootype.BuiltinType, ootype.StaticMethod)):
    #         assert isinstance(name_or_desc, str)
    #         name = name_or_desc
    #         if isinstance(TYPE, ootype.StaticMethod):
    #             METH = TYPE
    #         else:
    #             METH = oopspec.get_method(TYPE, name)
    #         class_name = self.lltype_to_cts(TYPE)
    #         if isinstance(TYPE, ootype.Dict):
    #             KEY = TYPE._KEYTYPE
    #             VALUE = TYPE._VALUETYPE
    #             name = name_or_desc
    #             if KEY is ootype.Void and VALUE is ootype.Void and name == 'll_get_items_iterator':
    #                 # ugly, ugly special case
    #                 ret_type = types.dict_items_iterator.specialize(types.int32, types.int32)
    #             elif VALUE is ootype.Void and METH.RESULT is ootype.Dict.VALUETYPE_T:
    #                 ret_type = types.void
    #             else:
    #                 ret_type = self.lltype_to_cts(METH.RESULT)
    #                 ret_type = dict_of_void_ll_copy_hack(TYPE, ret_type)
    #         else:
    #             ret_type = self.lltype_to_cts(METH.RESULT)
    #         generic_types = getattr(TYPE, '_generic_types', {})
    #         arg_types = [self.lltype_to_cts(arg).typename() for arg in METH.ARGS if
    #                      arg is not ootype.Void and \
    #                      generic_types.get(arg, arg) is not ootype.Void]
    #         arg_list = ', '.join(arg_types)
    #         return '%s %s::%s(%s)' % (ret_type, class_name, name, arg_list), False

    #     else:
    #         assert False

def dict_of_void_ll_copy_hack(TYPE, ret_type):
    # XXX: ugly hack to make the ll_copy signature correct when
    # CustomDict is special-cased to DictOfVoid.
    if isinstance(TYPE, ootype.CustomDict) and TYPE._VALUETYPE is ootype.Void:
        return ret_type.typename().replace('Dict`2', 'DictOfVoid`2')
    else:
        return ret_type
