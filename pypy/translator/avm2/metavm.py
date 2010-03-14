from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.metavm import MicroInstruction, \
     PushAllArgs, StoreResult, GetField, SetField, DownCast
from pypy.translator.oosupport.metavm import _Call as _OOCall
from pypy.translator.avm2.runtime import _static_meth, NativeInstance
from pypy.translator.avm2 import types_ as types
from mech.fusion.avm2 import constants

STRING_HELPER_CLASS = '[pypylib]pypy.runtime.String'

def functype_to_cts(cts, FUNC):
    ret_type = cts.lltype_to_cts(FUNC.RESULT)
    arg_types = [cts.lltype_to_cts(arg).typename()
                 for arg in FUNC.ARGS
                 if arg is not ootype.Void]
    return ret_type, arg_types

class _Call(_OOCall):
    
    def render(self, generator, op):
        callee = op.args[0].value
        if isinstance(callee, _static_meth):
            self._render_static_function(generator, callee, op.args)
        else:
            _OOCall.render(self, generator, op)

    def _render_static_function(self, generator, funcdesc, args):
        import pdb; pdb.set_trace()
        for func_arg in args[1:]: # push parameters
            self._load_arg_or_null(generator, func_arg)
        cts = generator.cts
        generator.emit()

    def _load_arg_or_null(self, generator, *args):
        for arg in args:
            if arg.concretetype is ootype.Void:
                if arg.value is None:
                    generator.ilasm.push_null() # special-case: use None as a null value
                else:
                    assert False, "Don't know how to load this arg"
            else:
                generator.load(arg)


class _CallMethod(_Call):
    def render(self, generator, op):
        method = op.args[0]
        self._render_method(generator, method.value, op.args[1:])

    def _render_method(self, generator, method_name, args):
        this = args[0]
        native = isinstance(this.concretetype, NativeInstance)
        if native:
            self._load_arg_or_null(generator, *args)
        else:
            generator.load(*args)

        if isinstance(this.concretetype, ootype.Array) and this.concretetype.ITEM is not ootype.Void:
            if method_name == "ll_setitem_fast":
                generator.array_setitem()
            elif method_name == "ll_getitem_fast":
                generator.array_getitem()
            elif method_name == "ll_length":
                generator.array_length()
            else:
                assert False
        elif isinstance(this.concretetype, ootype.AbstractString):
            if method_name == "ll_append":
                generator.emit('add')
            elif method_name == "ll_stritem_nonneg":
                generator.call_method("charAt", 1)
            elif method_name == "ll_strlen":
                generator.get_field("length")
        else:
            generator.call_method(method_name, len(args)-1)

class _IndirectCall(_CallMethod):
    def render(self, generator, op):
        # discard the last argument because it's used only for analysis
        self._render_method(generator, 'Invoke', op.args[:-1])

class ConstCall(MicroInstruction):
    def __init__(self, method, *args):
        self.__method = method
        self.__args = args

    def render(self, generator, op):
        generator.load(*self.__args)
        generator.call_method(self.__method, len(self.__args))

class ConstCallArgs(MicroInstruction):
    def __init__(self, method, numargs):
        self.__method = method
        self.__nargs = numargs

    def render(self, generator, op):
        generator.call_method(self.__method, self.__nargs)

class _RuntimeNew(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[0])
        generator.call_signature('object [pypylib]pypy.runtime.Utils::RuntimeNew(class [mscorlib]System.Type)')
        generator.cast_to(op.result.concretetype)

class _OOString(MicroInstruction):
    def render(self, generator, op):
        if op.args[1] == -1:
            generator.emit('findpropstrict', types.str_qname)
            generator.load(op.args[0])
            generator.emit('callproperty', types.str_qname, 1)
        else:
            generator.load(*op.args)
            generator.emit('callproperty', constants.QName("toString"), 1)

class _OOParseInt(MicroInstruction):
    def render(self, generator, op):
        generator.load(*op.args)
        generator.emit('getglobalscope')
        generator.emit('callproperty', constants.QName("parseInt"), 2)

class _OOParseFloat(MicroInstruction):
    def render(self, generator, op):
        generator.load(*op.args)
        generator.emit('getglobalscope')
        generator.emit('callproperty', constants.QName("parseFloat"), 1)

class PushClass(MicroInstruction):
    def __init__(self, classname):
        self.__class = constants.QName(classname)

    def render(self, generator, op):
        generator.emit('getlex', constants.QName(self.__class))

# class _NewCustomDict(MicroInstruction):
#     def render(self, generator, op):
#         DICT = op.args[0].value
#         comparer = EqualityComparer(generator.db, DICT._KEYTYPE,
#                                     (op.args[1], op.args[2], op.args[3]),
#                                     (op.args[4], op.args[5], op.args[6]))
#         generator.db.pending_node(comparer)
#         dict_type = generator.cts.lltype_to_cts(DICT)

#         generator.ilasm.new(comparer.get_ctor())
#         generator.ilasm.new('instance void %s::.ctor(class'
#                             '[mscorlib]System.Collections.Generic.IEqualityComparer`1<!0>)'
#                             % dict_type)

#XXX adapt to new way of things
#class _CastWeakAdrToPtr(MicroInstruction):
#    def render(self, generator, op):
#        RESULTTYPE = op.result.concretetype
#        resulttype = generator.cts.lltype_to_cts(RESULTTYPE)
#        generator.load(op.args[0])
#        generator.ilasm.call_method('object class %s::get_Target()' % WEAKREF, True)
#        generator.ilasm.opcode('castclass', resulttype)

# class MapException(MicroInstruction):
#     COUNT = 0
    
#     def __init__(self, instr, mapping):
#         if isinstance(instr, str):
#             self.instr = InstructionList([PushAllArgs, instr, StoreResult])
#         else:
#             self.instr = InstructionList(instr)
#         self.mapping = mapping

#     def render(self, generator, op):
#         ilasm = generator.ilasm
#         label = '__check_block_%d' % MapException.COUNT
#         MapException.COUNT += 1
#         ilasm.begin_try()
#         self.instr.render(generator, op)
#         ilasm.leave(label)
#         ilasm.end_try()
#         for cli_exc, py_exc in self.mapping:
#             ilasm.begin_catch(cli_exc)
#             ilasm.new('instance void class %s::.ctor()' % py_exc)
#             ilasm.opcode('throw')
#             ilasm.end_catch()
#         ilasm.label(label)
#         ilasm.opcode('nop')

# class _Box(MicroInstruction): 
#     def render(self, generator, op):
#         generator.load(op.args[0])
#         TYPE = op.args[0].concretetype
#         boxtype = generator.cts.lltype_to_cts(TYPE)
#         generator.ilasm.opcode('box', boxtype)

# class _Unbox(MicroInstruction):
#     def render(self, generator, op):
#         v_obj, v_type = op.args
#         assert v_type.concretetype is ootype.Void
#         TYPE = v_type.value
#         boxtype = generator.cts.lltype_to_cts(TYPE)
#         generator.load(v_obj)
#         generator.ilasm.opcode('unbox.any', boxtype)

class _NewArray(MicroInstruction):
    def render(self, generator, op):
        v_type, v_length = op.args
        assert v_type.concretetype is ootype.Void
        TYPE = v_type.value._INSTANCE
        generator.oonewarray(TYPE, v_length)

class _GetArrayElem(MicroInstruction):
    def render(self, generator, op):
        v_array, v_index = op.args
        generator.load(v_array)
        generator.get_field(str(v_index))

class _SetArrayElem(MicroInstruction):
    def render(self, generator, op):
        v_array, v_index, v_elem = op.args
        generator.load(v_array)
        if v_elem.concretetype is ootype.Void and v_elem.value is None:
            generator.push_null()
        else:
            generator.load(v_elem)
        generator.set_field(str(v_index))

class _TypeOf(MicroInstruction):
    def render(self, generator, op):
        c_type, = op.args
        assert c_type.concretetype is ootype.Void
        if isinstance(c_type.value, ootype.StaticMethod):
            FUNC = c_type.value
            fullname = generator.cts.lltype_to_cts(FUNC)
        else:
            cliClass = c_type.value
            fullname = cliClass._INSTANCE._name
        generator.gettype()

class _EventHandler(MicroInstruction):
    def render(self, generator, op):
        cts = generator.cts
        v_obj, c_methname = op.args
        assert c_methname.concretetype is ootype.Void
        TYPE = v_obj.concretetype
        classname = TYPE._name
        methname = 'o' + c_methname.value # XXX: do proper mangling
        _, meth = TYPE._lookup(methname)
        METH = ootype.typeOf(meth)
        ret_type, arg_types = functype_to_cts(cts, METH)
        arg_list = ', '.join(arg_types)
        generator.load(v_obj)
        desc = '%s class %s::%s(%s)' % (ret_type, classname, methname, arg_list)
        generator.ilasm.opcode('ldftn instance', desc)
        generator.ilasm.opcode('newobj', 'instance void class [mscorlib]System.EventHandler::.ctor(object, native int)')

class _GetStaticField(MicroInstruction):
    def render(self, generator, op):
        cts_class = op.args[0].value
        fldname = op.args[1].value
        generator.ilasm.load(cts_class)
        generator.ilasm.get_field(fldname)

class _SetStaticField(MicroInstruction):
    def render(self, generator, op):
        cts_class = op.args[0].value
        fldname = op.args[1].value
        generator.ilasm.load(cts_class)
        generator.ilasm.swap()
        generator.ilasm.set_field(fldname)

class _FieldInfoForConst(MicroInstruction):
    def render(self, generator, op):
        from pypy.translator.cli.constant import CONST_CLASS
        llvalue = op.args[0].value
        constgen = generator.db.constant_generator
        const = constgen.record_const(llvalue)
        generator.ilasm.opcode('ldtoken', CONST_CLASS)
        generator.ilasm.call('class [mscorlib]System.Type class [mscorlib]System.Type::GetTypeFromHandle(valuetype [mscorlib]System.RuntimeTypeHandle)')
        generator.ilasm.opcode('ldstr', '"%s"' % const.name)
        generator.ilasm.call_method('class [mscorlib]System.Reflection.FieldInfo class [mscorlib]System.Type::GetField(string)', virtual=True)


# OOTYPE_TO_MNEMONIC = {
#     ootype.Bool: 'i1', 
#     ootype.Char: 'i2',
#     ootype.UniChar: 'i2',
#     ootype.Signed: 'i4',
#     ootype.SignedLongLong: 'i8',
#     ootype.Unsigned: 'u4',
#     ootype.UnsignedLongLong: 'u8',
#     ootype.Float: 'r8',
#     }

# class _CastPrimitive(MicroInstruction):
#     def render(self, generator, op):
#         TO = op.result.concretetype
#         mnemonic = OOTYPE_TO_MNEMONIC[TO]
#         generator.ilasm.opcode('conv.%s' % mnemonic)

Call = _Call()
CallMethod = _CallMethod()
IndirectCall = _IndirectCall()
RuntimeNew = _RuntimeNew()
#CastWeakAdrToPtr = _CastWeakAdrToPtr()
NewArray = _NewArray()
GetArrayElem = _GetArrayElem()
SetArrayElem = _SetArrayElem()
TypeOf = _TypeOf()
EventHandler = _EventHandler()
GetStaticField = _GetStaticField()
SetStaticField = _SetStaticField()
FieldInfoForConst = _FieldInfoForConst()
OOString = _OOString()
OOParseInt = _OOParseInt()
OOParseFloat = _OOParseFloat()
# CastPrimitive = _CastPrimitive()
