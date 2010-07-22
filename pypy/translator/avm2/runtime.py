import types

from pypy.tool.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInstance, SomeOOInstance, SomeInteger, s_None,\
     s_ImpossibleValue, lltype_to_annotation, annotation_to_lltype, SomeChar, SomeString

from pypy.annotation import model as annmodel

from pypy.rpython.error import TyperError
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rmodel import Repr
from pypy.rpython.rint import IntegerRepr
from pypy.rpython.ootypesystem.rootype import OOInstanceRepr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import Meth, StaticMethod

## Annotation model

class SomeAVM2Class(SomeObject):
    def getattr(self, s_attr):
        assert self.is_constant()
        assert s_attr.is_constant()
        nativeclass = self.const
        attrname = s_attr.const
        if attrname in nativeclass._static_fields:
            return nativeclass._static_fields[attrname]
        elif attrname in nativeclass._static_methods:
            return SomeAVM2StaticMethod(nativeclass, attrname)
        else:
            return s_ImpossibleValue

    def setattr(self, s_attr, s_value):
        assert self.is_constant()
        assert s_attr.is_constant
        nativeclass = self.const
        attrname = s_attr.const
        if attrname not in nativeclass._static_fields:
            return s_ImpossibleValue
        # XXX: check types?

    def simple_call(self, *s_args):
        assert self.is_constant()
        return SomeOOInstance(self.const._INSTANCE)

    def rtyper_makerepr(self, rtyper):
        return AVM2ClassRepr(self.const)

    def rtyper_makekey(self):
        return self.__class__, self.const


class SomeAVM2StaticMethod(SomeObject):
    def __init__(self, native_class, meth_name):
        self.native_class = native_class
        self.meth_name = meth_name

    def simple_call(self, *args_s):
        return self.native_class._ann_static_method(self.meth_name, args_s)

    def rtyper_makerepr(self, rtyper):
        return AVM2StaticMethodRepr(self.native_class, self.meth_name)

    def rtyper_makekey(self):
        return self.__class__, self.native_class, self.meth_name

# class __extend__(SomeOOInstance):

#     def simple_call(self, *s_args):
#         from pypy.translator.cli.query import get_cli_class
#         DELEGATE = get_cli_class('System.Delegate')._INSTANCE
#         if ootype.isSubclass(self.ootype, DELEGATE):
#             s_invoke = self.getattr(immutablevalue('Invoke'))
#             return s_invoke.simple_call(*s_args)
#         else:
#             # cannot call a non-delegate
#             return SomeObject.simple_call(self, *s_args)

class __extend__(pairtype(SomeOOInstance, SomeInteger)):
    def getitem((ooinst, index)):
        if ooinst.ootype._isArray:
            return SomeOOInstance(ooinst.ootype._ELEMENT)
        return s_ImpossibleValue

    def setitem((ooinst, index), s_value):
        if ooinst.ootype._isArray:
            if s_value is annmodel.s_None:
                return s_None
            ELEMENT = ooinst.ootype._ELEMENT
            VALUE = s_value.ootype
            assert ootype.isSubclass(VALUE, ELEMENT)
            return s_None
        return s_ImpossibleValue


## Rtyper model

class AVM2ClassRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, native_class):
        self.native_class = native_class

    def rtype_getattr(self, hop):
        attrname = hop.args_v[1].value
        if attrname in self.native_class._static_methods:
            return hop.inputconst(ootype.Void, self.native_class)
        else:
            assert attrname in self.native_class._static_fields
            TYPE = self.native_class._static_fields[attrname]
            c_class = hop.inputarg(hop.args_r[0], arg=0)
            c_name = hop.inputconst(ootype.Void, attrname)
            return hop.genop("getstaticfield", [c_class, c_name], resulttype=hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        attrname = hop.args_v[1].value
        assert attrname in self.native_class._static_fields
        c_class = hop.inputarg(hop.args_r[0], arg=0)
        c_name = hop.inputconst(ootype.Void, attrname)
        v_value = hop.inputarg(hop.args_r[2], arg=2)
        return hop.genop("setstaticfield", [c_class, c_name, v_value], resulttype=hop.r_result.lowleveltype)

    def rtype_simple_call(self, hop):
        INSTANCE = hop.args_r[0].native_class._INSTANCE
        cINST = hop.inputconst(ootype.Void, INSTANCE)
        vlist = hop.inputargs(*hop.args_r)[1:] # discard the first argument
        hop.exception_is_here()
        return hop.genop("new", [cINST]+vlist, resulttype=hop.r_result.lowleveltype)

class AVM2StaticMethodRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, native_class, meth_name):
        self.native_class = native_class
        self.meth_name = meth_name

    def _build_desc(self, args_v):
        ARGS = tuple([v.concretetype for v in args_v])
        return self.native_class._lookup(self.meth_name, ARGS)

    def rtype_simple_call(self, hop):
        vlist = []
        for i, repr in enumerate(hop.args_r[1:]):
            vlist.append(hop.inputarg(repr, i+1))
        resulttype = hop.r_result.lowleveltype
        desc = self._build_desc(vlist)
        cDesc = hop.inputconst(ootype.Void, desc)
        return hop.genop("direct_call", [cDesc] + vlist, resulttype=resulttype)


class __extend__(pairtype(OOInstanceRepr, IntegerRepr)):

    def rtype_getitem((r_inst, r_int), hop):
        v_array, v_index = hop.inputargs(r_inst, ootype.Signed)
        hop.exception_is_here()
        return hop.genop('getelem', [v_array, v_index], hop.r_result.lowleveltype)

    def rtype_setitem((r_inst, r_int), hop):
        vlist = hop.inputargs(*hop.args_r)
        hop.exception_is_here()
        return hop.genop('setelem', vlist, hop.r_result.lowleveltype)


class __extend__(OOInstanceRepr):

    def rtype_len(self, hop):
        if not self.lowleveltype._isArray:
            raise TypeError("len() on a non-array instance")
        vlist = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        return hop.genop('arraylength', vlist, hop.r_result.lowleveltype)

    ## def rtype_simple_call(self, hop):
    ##     TYPE = self.lowleveltype
    ##     ARGS = tuple([repr.lowleveltype for repr in hop.args_r[1:]])
    ##     vlist = hop.inputargs(self, *hop.args_r[1:])
    ##     hop.exception_is_here()
    ##     return hop.genop("oosend", [cname]+vlist,
    ##                      resulttype = hop.r_result.lowleveltype)


## OOType model

class _static_meth(object):

    def __init__(self, TYPE):
        self._TYPE = TYPE

    def _set_attrs(self, cls, name):
        self._cls = cls
        self._name = name

    def _get_desc(self, ARGS):
        #assert ARGS == self._TYPE.ARGS
        return self

class AVM2Instance(ootype.Instance):
    def __init__(self, namespace, name, superclass,
                 fields={}, methods={}, _is_root=False, _hints = {}):
        fullname = '%s.%s' % (namespace, name)
        self._namespace = namespace
        self._classname = name
        self._is_value_type = False
        ootype.Instance.__init__(self, fullname, superclass, fields, methods, _is_root, _hints)


## RPython interface definition

class AVM2Class(object):
    def __init__(self, INSTANCE, static_methods, static_fields):
        self._name = INSTANCE._name
        self._INSTANCE = INSTANCE
        self._static_methods = {}
        self._static_fields = {}
        self._add_methods(static_methods)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._INSTANCE._name)

    def _add_methods(self, methods):
        self._static_methods.update(methods)
        for name, meth in methods.iteritems():
            meth._set_attrs(self, name)

    def _add_static_fields(self, fields):
        self._static_fields.update(fields)

    def _lookup(self, meth_name, ARGS):
        meth = self._static_methods[meth_name]
        return meth._get_desc(ARGS)

    def _ann_static_method(self, meth_name, args_s):
        meth = self._static_methods[meth_name]
        return meth._resolver.annotate(args_s)


class Entry(ExtRegistryEntry):
    _type_ = AVM2Class

    def compute_annotation(self):
        return SomeAVM2Class()

    def compute_result_annotation(self):
        return SomeOOInstance(self.instance._INSTANCE)


def new_array(type, length):
    return [None] * length

def init_array(type, *args):
    # PythonNet doesn't provide a straightforward way to create arrays... fake it with a list
    return list(args)

class Entry(ExtRegistryEntry):
    _about_ = new_array

    def compute_result_annotation(self, type_s, length_s):
        from pypy.translator.avm2.query import get_native_class
        assert type_s.is_constant()
        assert isinstance(length_s, SomeInteger)
        TYPE = type_s.const._INSTANCE
        fullname = '%s.%s[]' % (TYPE._namespace, TYPE._classname)
        Array = get_native_class(fullname)
        return SomeOOInstance(Array._INSTANCE)

    def specialize_call(self, hop):
        c_type, v_length = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        return hop.genop('newvector', [c_type, v_length], hop.r_result.lowleveltype)


class Entry(ExtRegistryEntry):
    _about_ = init_array

    def compute_result_annotation(self, type_s, *args_s):
        from pypy.translator.avm2.query import get_native_class
        assert type_s.is_constant()
        TYPE = type_s.const._INSTANCE
        for i, arg_s in enumerate(args_s):
            if TYPE is not arg_s.ootype:
                raise TypeError, 'Wrong type of arg #%d: %s expected, %s found' % \
                      (i, TYPE, arg_s.ootype)
        fullname = '%s.%s[]' % (TYPE._namespace, TYPE._classname)
        Array = get_native_class(fullname)
        return SomeOOInstance(Array._INSTANCE)

    def specialize_call(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        c_type, v_elems = vlist[0], vlist[1:]
        c_length = hop.inputconst(ootype.Signed, len(v_elems))
        hop.exception_cannot_occur()
        v_array = hop.genop('avm2_initvector', [c_type, v_elems], hop.r_result.lowleveltype)
        return v_array

# def typeof(Class_or_type):
#     # if isinstance(Class_or_type, ootype.StaticMethod):
#     #     FUNCTYPE = Class_or_type
#     #     Class = known_delegates[FUNCTYPE]
#     # else:
#     #     assert isinstance(Class_or_type, CliClass)
#     #     Class = Class_or_type
#     # TYPE = Class._INSTANCE
#     # return PythonNet.System.Type.GetType(TYPE._assembly_qualified_name)
#     return None

# def classof(cliClass_or_type):
#     if isinstance(cliClass_or_type, ootype.StaticMethod):
#         try:
#             FUNC = cliClass_or_type
#             return known_delegates_class[FUNC]
#         except KeyError:
#             cls = ootype._class(ootype.ROOT)
#             cls._FUNC = FUNC
#             known_delegates_class[FUNC] = cls
#             return cls
#     else:
#         assert isinstance(cliClass_or_type, CliClass)
#         TYPE = cliClass_or_type._INSTANCE
#         return ootype.runtimeClass(TYPE)

# class Entry(ExtRegistryEntry):
#     _about_ = typeof

#     def compute_result_annotation(self, Class_s):
#         from pypy.translator.avm2.query import get_native_class
#         assert Class_s.is_constant()
#         Type = playerglobal.Class
#         return SomeOOInstance(Type._INSTANCE)

#     def specialize_call(self, hop):
#         v_type, = hop.inputargs(*hop.args_r)
#         return hop.genop('typeof', [v_type], hop.r_result.lowleveltype)


# def eventhandler(obj):
#     return CLR.System.EventHandler(obj)

# class Entry(ExtRegistryEntry):
#     _about_ = eventhandler

#     def compute_result_annotation(self, s_value):
#         from pypy.translator.cli.query import get_cli_class
#         cliType = get_cli_class('System.EventHandler')
#         return SomeOOInstance(cliType._INSTANCE)

#     def specialize_call(self, hop):
#         v_obj, = hop.inputargs(*hop.args_r)
#         methodname = hop.args_r[0].methodname
#         c_methodname = hop.inputconst(ootype.Void, methodname)
#         return hop.genop('cli_eventhandler', [v_obj, c_methodname], hop.r_result.lowleveltype)


## def clidowncast(obj, TYPE):
##     return obj

## class Entry(ExtRegistryEntry):
##     _about_ = clidowncast

##     def compute_result_annotation(self, s_value, s_type):
##         if isinstance(s_type.const, ootype.OOType):
##             TYPE = s_type.const
##         else:
##             Class = s_type.const
##             TYPE = Class._INSTANCE
##         assert ootype.isSubclass(TYPE, s_value.ootype)
##         return SomeOOInstance(TYPE)

##     def specialize_call(self, hop):
##         assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
##         v_inst = hop.inputarg(hop.args_r[0], arg=0)
##         return hop.genop('oodowncast', [v_inst], resulttype = hop.r_result.lowleveltype)

## def cast_record_to_object(record):
##     T = ootype.typeOf(record)
##     assert isinstance(T, ootype.Record)
##     return ootype._view(playerglobal.Object._INSTANCE, record)

## def cast_object_to_record(T, obj):
##     assert isinstance(T, ootype.Record)
##     assert isinstance(obj, ootype._view)
##     assert isinstance(obj._inst, ootype._record)
##     record = obj._inst
##     assert ootype.typeOf(record) == T
##     return record

## class Entry(ExtRegistryEntry):
##     _about_ = cast_record_to_object

##     def compute_result_annotation(self, s_value):
##         T = s_value.ootype
##         assert isinstance(T, ootype.Record)
##         can_be_None = getattr(s_value, 'can_be_None', False)
##         return SomeOOInstance(playerglobal.Object._INSTANCE, can_be_None=can_be_None)

##     def specialize_call(self, hop):
##         assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
##         v_obj, = hop.inputargs(*hop.args_r)
##         hop.exception_cannot_occur()
##         return hop.genop('ooupcast', [v_obj], hop.r_result.lowleveltype)

## class Entry(ExtRegistryEntry):
##     _about_ = cast_object_to_record

##     def compute_result_annotation(self, s_type, s_value):
##         assert s_type.is_constant()
##         T = s_type.const
##         assert isinstance(T, ootype.Record)
##         can_be_None = getattr(s_value, 'can_be_None', False)
##         return SomeOOInstance(T, can_be_None)

##     def specialize_call(self, hop):
##         assert hop.args_s[0].is_constant()
##         TYPE = hop.args_s[0].const
##         v_obj = hop.inputarg(hop.args_r[1], arg=1)
##         return hop.genop('oodowncast', [v_obj], hop.r_result.lowleveltype)

#class _fieldinfo(object):
#     def __init__(self, llvalue):
#         self._TYPE = CLR.System.Reflection.FieldInfo._INSTANCE
#         self.llvalue = llvalue

# def fieldinfo_for_const(const):
#     return _fieldinfo(const)

# class Entry(ExtRegistryEntry):
#     _about_ = fieldinfo_for_const

#     def compute_result_annotation(self, s_const):
#         assert s_const.is_constant()
#         return SomeOOInstance(CLR.System.Reflection.FieldInfo._INSTANCE)

#     def specialize_call(self, hop):
#         llvalue = hop.args_v[0].value
#         c_llvalue = hop.inputconst(ootype.Void, llvalue)
#         return hop.genop('cli_fieldinfo_for_const', [c_llvalue], resulttype = hop.r_result.lowleveltype)


# class Entry(ExtRegistryEntry):
#     _type_ = _fieldinfo

#     def compute_annotation(self):
#         return SomeOOInstance(CLR.System.Reflection.FieldInfo._INSTANCE)

# known_delegates = {
#     ootype.StaticMethod([ootype.Signed], ootype.Signed):       CLR.pypy.test.DelegateType_int__int_1,
#     ootype.StaticMethod([ootype.Signed] * 2, ootype.Signed):   CLR.pypy.test.DelegateType_int__int_2,
#     ootype.StaticMethod([ootype.Signed] * 3, ootype.Signed):   CLR.pypy.test.DelegateType_int__int_3,
#     ootype.StaticMethod([ootype.Signed] * 5, ootype.Signed):   CLR.pypy.test.DelegateType_int__int_5,
#     ootype.StaticMethod([ootype.Signed] * 27, ootype.Signed):   CLR.pypy.test.DelegateType_int__int_27,
#     ootype.StaticMethod([ootype.Signed] * 100, ootype.Signed): CLR.pypy.test.DelegateType_int__int_100
#     }

# known_delegates_class = {}

