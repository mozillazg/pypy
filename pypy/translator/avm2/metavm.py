
from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow.model import Constant
from pypy.translator.oosupport.metavm import MicroInstruction, _Call as _OOCall
from pypy.translator.avm2.runtime import _static_meth
from pypy.translator.avm2.rlib import RLib
from pypy.translator.avm2.types_ import types

from mech.fusion.avm2.interfaces import IMultiname

class AddSub(MicroInstruction):
    def __init__(self, int, add):
        if int:
            if add:
                self.p1, self.n1 = 'increment_i', 'decrement_i'
            else:
                self.p1, self.n1 = 'decrement_i', 'increment_i'
        else:
            if add:
                self.p1, self.n1 = 'increment', 'decrement'
            else:
                self.p1, self.n1 = 'decrement', 'increment'

    def render(self, generator, op):
        if isinstance(op.args[1], Constant):
            if op.args[1].value == 1:
                generator.load(op.args[0])
                generator.emit(self.p1)
            elif op.args[1].value == -1:
                generator.load(op.args[0])
                generator.emit(self.n1)
        for arg in op.args:
            generator.load(arg)
        generator.emit('add')

class _Call(_OOCall):
    def render(self, generator, op):
        callee = op.args[0].value
        if isinstance(callee, _static_meth):
            self._render_static_function(generator, callee, op.args)
        else:
            generator.call_graph(op.args[0].value.graph, op.args[1:])

    def _render_static_function(self, generator, funcdesc, args):
        cts = generator.cts
        generator.load(*args[1:])
        generator.emit()

class _CallMethod(_Call):
    donothing = object()
    ONELINER = {
        "list_ll_length": lambda gen,a: gen.get_field("length", types.int),

        "str_ll_append": lambda gen,a: gen.emit('add'),
        "str_ll_strlen": lambda gen,a: gen.get_field("length", types.int),
        "str_ll_stritem_nonneg": lambda gen,a: gen.call_method("charAt", 1, types.string),
        "str_ll_strconcat": lambda gen,a: gen.emit('add'),
        "str_ll_streq": lambda gen,a: gen.emit('equals'),
        "str_ll_strcmp": lambda gen,a: gen.call_method("localeCompare", 1, types.int),

        "stringbuilder_ll_allocate": donothing,
        "stringbuilder_ll_build": donothing,
    }
    def render(self, generator, op):
        method = op.args[0]
        self._render_method(generator, method.value, op.args[1:])

    def _render_method(self, generator, method_name, args):
        DISPATCH, meth = self.ONELINER, args[0].concretetype.oopspec_name+'_'+method_name
        if meth in DISPATCH:
            generator.load(*args)
            if DISPATCH[meth] is not self.donothing:
                DISPATCH[meth](generator, args)
        elif getattr(generator, meth, None):
            getattr(generator, meth)(args)
        elif meth in RLib:
            RLib[meth](generator, *args)
        else:
            # storeresult expects something on the stack
            generator.push_null()

class _IndirectCall(_CallMethod):
    def render(self, generator, op):
        # discard the last argument because it's used only for analysis
        assert False
        self._render_method(generator, 'Invoke', op.args[:-1])

class ConstCall(MicroInstruction):
    def __init__(self, method, *args):
        self.__method = method
        self.__args = args

    def render(self, generator, op):
        generator.call_method_constargs(self.__method, None, *self.__args)

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
        obj, base = op.args
        if base == -1 or (isinstance(base, Constant) and base.value == -1):
            if isinstance(obj.concretetype, ootype.Instance):
                generator.load("<")
                generator.call_method_constargs('getName', obj)
                generator.emit('add')
                generator.load(" object>")
                generator.emit('add')
            else:
                generator.call_method_constargs('toString', obj)
        else:
            generator.call_method_constargs('toString', obj, base)

class _OOParseInt(MicroInstruction):
    def render(self, generator, op):
        generator.call_function_constargs('parseInt', *op.args)

class _OOParseFloat(MicroInstruction):
    def render(self, generator, op):
        generator.call_function_constargs('parseFloat', *op.args)

class _SetField(MicroInstruction):
    def render(self, generator, op):
        this, field, value = op.args
        if value.concretetype is ootype.Void:
            return
        generator.load(this)
        generator.load(value)
        generator.set_field(field.value)

class _GetField(MicroInstruction):
    def render(self, generator, op):
        # OOType produces void values on occassion that can safely be ignored
        if op.result.concretetype is ootype.Void:
            return
        this, field = op.args
        generator.load(this)
        generator.get_field(field.value)


class PushClass(MicroInstruction):
    def __init__(self, classname):
        self.__class = IMultiname(classname)

    def render(self, generator, op):
        generator.load(self.__class)

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
        generator.gettype()

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
GetStaticField = _GetStaticField()
SetStaticField = _SetStaticField()
OOString = _OOString()
OOParseInt = _OOParseInt()
OOParseFloat = _OOParseFloat()
# CastPrimitive = _CastPrimitive()
GetField = _GetField()
SetField = _SetField()
