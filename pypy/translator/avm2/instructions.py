
from pypy.translator.avm2.util import serialize_u32 as u32, Avm2Label
from pypy.translator.avm2.constants import METHODFLAG_Activation, METHODFLAG_SetsDxns
from decorator import decorator

INSTRUCTIONS = {}

@decorator
def needs_specialized(fn, self, *args, **kwargs):
      if not self.specialized:
            raise ValueError, "Instruction needs to be specialized"
      return fn(self, *args, **kwargs)

class _Avm2ShortInstruction(object):
      specialized = False
      def __init__(self, opcode, name, stack=0, scope=0, flags=0):
            self.opcode = opcode
            self.name   = name
            self.stack  = stack
            self.scope  = scope
            self.flags  = flags

            INSTRUCTIONS[opcode] = self

      def _repr(self):
            return "%s (0x%H)" % (self.name, self.opcode)
      
      def _set_assembler_props(self, asm):
            asm.flags |= self.flags
            asm.stack_depth += self.stack
            asm.scope_depth += self.scope

      def _serialize(self):
            return chr(self.opcode)

      serialize = _serialize
      set_assembler_props = _set_assembler_props
      __repr__ = _repr
      
      def specialize(self, **kwargs):
            return type("Avm2_%s_Instruction" % self.name,
                        (self.__class__), dict(kwargs.items(),
                            specialized=True,
                            serialize=self._serialize,
                            set_assembler_props=self._set_assembler_props,
                            __repr__=self._repr))

class _Avm2DebugInstruction(_Avm2ShortInstruction):
      @needs_specialized
      def _serialize(self):
            return chr(self.opcode) + \
                   chr(self.debug_type & 0xFF) + \
                   u32(self.index) + \
                   chr(self.reg & 0xFF) + \
                   u32(self.extra)

class _Avm2U8Instruction(_Avm2ShortInstruction):
      @needs_specialized
      def _serialize(self):
            return chr(self.opcode) + chr(self.argument)
      
      def __call__(self, argument):
            return self.specialize(argument=argument)

class _Avm2U30Instruction(_Avm2U8Instruction):
      @needs_specialized
      def _serialize(self):
            if hasattr(self.argument, "__iter__"):
                  return chr(self.opcode) + ''.join(u32(i) for i in self.argument)
            else:
                  return chr(self.opcode) + u32(self.argument)

      def __call__(self, argument, *arguments):
            if arguments:
                  self.argument = [argument] + list(arguments)
            else:
                  self.argument = argument

class _Avm2KillInstruction(_Avm2U30Instruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            super(_Avm2KillInstruction, self)._set_assembler_props(asm)
            asm.kill_local(self.argument)

class _Avm2NamespaceInstruction(_Avm2U30Instruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            super(_Avm2NamespaceInstruction, self)._set_assembler_props(asm)
            has_rtns   = asm.constants.has_RTNS(self.argument)
            has_rtname = asm.constants.has_RTName(self.argument)

            asm.stack_depth -= int(has_rtns) + int(has_rtname)

class _Avm2SetLocalInstruction(_Avm2U30Instruction):
      @needs_specialized
      def __call__(self, index):
            _speed = {0: setlocal_0, 1: setlocal_1, 2: setlocal_2, 3: setlocal_3}
            if index in _speed:
                  return _speed[index]
            return self.specialize(index=index)

class _Avm2GetLocalInstruction(_Avm2ShortInstruction):
      def __call__(self, index):
            _speed = {0: getlocal_0, 1: getlocal_1, 2: getlocal_2, 3: getlocal_3}
            if index in _speed:
                  return _speed[index]
            return self.specialize(index=index)

class _Avm2OffsetInstruction(_Avm2ShortInstruction):
      @needs_specialized
      def _repr(self):
            return repr(super(_Avm2OffsetInstruction, self))[:-2] + " lbl=%r)>" % self.lbl
      
      @needs_specialized
      def _set_assembler_props(self, asm):
            super(_Avm2OffsetInstruction, self)._set_assembler_props
            if self.lbl is None:
                  self.lbl = Avm2Label(asm)
                  self.asm = asm
      
      @needs_specialized
      def _serialize(self):
            code = chr(self.opcode)
            code += self.lbl.write_relative_offset(len(self.asm) + 4, len(self.asm) + 1)
            return code
      
      def __call__(self, lbl=None):
            return self.specialize(lbl=lbl)

class _Avm2LookupSwitchInstruction(_Avm2ShortInstruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            super(_Avm2LookupSwitchInstruction, self)._set_assembler_props(asm)
            self.asm = asm
            if self.default_label is None:
                  self.default_label = Avm2Label(asm)
            if isinstance(self.case_labels, int):
                  self.case_labels = [Avm2Label(asm) for i in xrange(self.case_labels)]
                  
      @needs_specialized
      def _serialize(self):
            code = chr(self.opcode)
            base = len(self.asm)
            code += self.default_label.write_relative_offset(base, base+1)
            code += u32(len(self.case_labels) - 1)
            
            for lbl in self.case_labels:
                  location = base + len(code)
                  code += lbl.write_relative_offset(base, location)
            return code
                  
      def __call__(self, default_label=None, case_labels=None):
            return self.specialize(default_label=default_label, case_labels=case_labels)

class _Avm2LabelInstruction(_Avm2ShortInstruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            super(_Avm2LabelInstruction, self)._set_assembler_props(asm)
            if self.lbl == None:
                  self.define = True
                  self.lbl = Avm2Label(asm)
            else:
                  assert self.lbl.address == -1
                  asm.stack_depth = self.lbl.stack_depth
                  asm.scope_depth = self.lbl.scope_depth
            self.lbl.address = len(asm)

      @needs_specialized
      def _serialize(self):
            if self.define:
                  return label_internal.serialize()
            return ""
      
      def __call__(self, lbl=None):
            return self.specialize(lbl=lbl, define=False)

class _Avm2Call(_Avm2U30Instruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            asm.stack_depth += 1 - (self.argument + 2) # push function/receiver/args; push result
      
class _Avm2Construct(_Avm2U30Instruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            asm.stack_depth += 1 - (self.argument + 1) # push object/args; push result
      
class _Avm2ConstructSuper(_Avm2U30Instruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            asm.stack_depth += self.argument + 1 # pop receiver/args

class _Avm2CallIDX(_Avm2U30Instruction):
      @needs_specialized
      def _serialize(self):
            return chr(self.opcode) + u32(self.index) + u32(self.argument)

      @needs_specialized
      def _set_assembler_props(self, asm):
            asm.stack_depth += 1 - (self.argument + 1) # push object/args; push result
      
      def __call__(self, index, num_args):
            return self.specialize(index=index, argument=num_args)

class _Avm2CallMN(_Avm2CallIDX):
      @needs_specialized
      def _set_assembler_props(self, asm):
            has_rtns = asm.constants.has_rtns(self.index)
            has_rtname = asm.constants.has_rtname(self.index)
            asm.stack_depth += int(self.is_void) - (1 + int(has_rtns) + int(has_rtname) + self.argument)

      def __call__(self, index, num_args, is_void):
            return self.specialize(index=index, argument=num_args, is_void=is_void)

class _Avm2NewArray(_Avm2U30Instruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            asm.stack_depth += 1 - self.argument

class _Avm2NewObject(_Avm2U30Instruction):
      @needs_specialized
      def _set_assembler_props(self, asm):
            asm.stack_depth += 1 - (2 * self.argument)

#{ Instructions that push one value to the stack and take no arguments.
dup = _Avm2ShortInstruction(0x2A, "dup", 1)
getglobalscope = _Avm2ShortInstruction(0x6A, "getglobalscope", 1)
getlocal_0 = _Avm2ShortInstruction(0xD0, "getlocal_0", 1)
getlocal_1 = _Avm2ShortInstruction(0xD1, 'getlocal_1', 1)
getlocal_2 = _Avm2ShortInstruction(0xD2, 'getlocal_2', 1)
getlocal_3 = _Avm2ShortInstruction(0xD3, 'getlocal_3', 1)
newactivation = _Avm2ShortInstruction(0x57, 'newactivation', 1, flags=METHODFLAG_Activation)
pushfalse = _Avm2ShortInstruction(0x27, 'pushfalse', 1)
pushnan = _Avm2ShortInstruction(0x28, 'pushnan', 1)
pushnull = _Avm2ShortInstruction(0x20, 'pushnull', 1)
pushtrue = _Avm2ShortInstruction(0x26, 'pushtrue', 1)
pushundefined = _Avm2ShortInstruction(0x21, 'pushundefined', 1)
#}

#{ Instructions that pop one value from the stack and take no arguments.
add = _Avm2ShortInstruction(0xA0, 'add', -1)
add_i = _Avm2ShortInstruction(0xC5, 'add_i', -1)
astypelate = _Avm2ShortInstruction(0x87, 'astypelate', -1)
bitand = _Avm2ShortInstruction(0xA8, 'bitand', -1)
bitor = _Avm2ShortInstruction(0xA9, 'bitor', -1)
bitxor = _Avm2ShortInstruction(0xAA, 'bitxor', -1)
divide = _Avm2ShortInstruction(0xA3, 'divide', -1)
dxnslate = _Avm2ShortInstruction(0x07, 'dxnslate', -1, flags=METHODFLAG_SetsDxns)
equals = _Avm2ShortInstruction(0xAB, 'equals', -1)
greaterequals = _Avm2ShortInstruction(0xB0, 'greaterequals', -1)
greaterthan = _Avm2ShortInstruction(0xAF, 'greaterthan', -1)
hasnext = _Avm2ShortInstruction(0x1F, 'hasnext', -1)
if_ = _Avm2ShortInstruction(0xB4, 'in', -1)
instanceof = _Avm2ShortInstruction(0xB1, 'instanceof', -1)
istypelate = _Avm2ShortInstruction(0xB3, 'istypelate', -1)
lessequals = _Avm2ShortInstruction(0xAE, 'lessequals', -1)
lessthan = _Avm2ShortInstruction(0xAD, 'lessthan', -1)
lshift = _Avm2ShortInstruction(0xA5, 'lshift', -1)
modulo = _Avm2ShortInstruction(0xA4, 'modulo', -1)
multiply = _Avm2ShortInstruction(0xA2, 'multiply', -1)
multiply_i = _Avm2ShortInstruction(0xC7, 'multiply_i', -1)
nextname = _Avm2ShortInstruction(0x1E, 'nextname', -1)
nextvalue = _Avm2ShortInstruction(0x23, 'nextvalue', -1)
pop = _Avm2ShortInstruction(0x29, 'pop', -1)
pushscope = _Avm2ShortInstruction(0x30, 'pushscope', -1, 1) # Changes scope depth.
pushwith = _Avm2ShortInstruction(0x1C, 'pushwith', -1, 1) # Changes scope depth.
returnvalue = _Avm2ShortInstruction(0x48, 'returnvalue', -1)
rshift = _Avm2ShortInstruction(0xA6, 'rshift', -1)
setlocal_0 = _Avm2ShortInstruction(0xD4, 'setlocal_0', -1)
setlocal_1 = _Avm2ShortInstruction(0xD5, 'setlocal_1', -1)
setlocal_2 = _Avm2ShortInstruction(0xD6, 'setlocal_2', -1)
setlocal_3 = _Avm2ShortInstruction(0xD7, 'setlocal_3', -1)
strictequals = _Avm2ShortInstruction(0xAC, 'strictequals', -1)
subtract = _Avm2ShortInstruction(0xA1, 'subtract', -1)
subtract_i = _Avm2ShortInstruction(0xC6, 'subtract_i', -1)
throw = _Avm2ShortInstruction(0x03, 'throw', -1)
urshift = _Avm2ShortInstruction(0xA7, 'urshift', -1)
#}

#{ Instructions that do not change the stack height and take no arguments.
bitnot = _Avm2ShortInstruction(0x97, 'bitnot')
checkfilter = _Avm2ShortInstruction(0x78, 'checkfilter')
coerce_a = _Avm2ShortInstruction(0x82, 'coerce_a')
coerce_s = _Avm2ShortInstruction(0x85, 'coerce_s')
convert_b = _Avm2ShortInstruction(0x76, 'convert_b')
convert_d = _Avm2ShortInstruction(0x75, 'convert_d')
convert_i = _Avm2ShortInstruction(0x73, 'convert_i')
convert_o = _Avm2ShortInstruction(0x77, 'convert_o')
convert_s = _Avm2ShortInstruction(0x70, 'convert_s')
convert_u = _Avm2ShortInstruction(0x74, 'convert_u')
decrement = _Avm2ShortInstruction(0x93, 'decrement')
decrement_i = _Avm2ShortInstruction(0xC1, 'decrement_i')
esc_xattr = _Avm2ShortInstruction(0x72, 'esc_xattr')
esc_xelem = _Avm2ShortInstruction(0x71, 'esc_xelem')
increment = _Avm2ShortInstruction(0x91, 'increment')
increment_i = _Avm2ShortInstruction(0xC0, 'increment_i')
# kill moved down to Special.
negate = _Avm2ShortInstruction(0x90, 'negate')
negate_i = _Avm2ShortInstruction(0xC4, 'negate_i')
nop = _Avm2ShortInstruction(0x02, 'nop')
not_ = _Avm2ShortInstruction(0x96, 'not')
popscope = _Avm2ShortInstruction(0x1D, 'popscope', 0, -1) # Changes scope depth.
returnvoid = _Avm2ShortInstruction(0x47, 'returnvoid')
swap = _Avm2ShortInstruction(0x2B, 'swap')
typeof = _Avm2ShortInstruction(0x95, 'typeof')
#}

#{ Call Instructions
call = _Avm2Call(0x41, 'call')
construct = _Avm2Construct(0x42, 'construct')
constructsuper = _Avm2ConstructSuper(0x49, 'constructsuper')

callmethod = _Avm2CallIDX(0x43, 'callmethod')
callstatic = _Avm2CallIDX(0x43, 'callstatic')

callsuper = _Avm2CallMN(0x45, 'callsuper')
callproperty = _Avm2CallMN(0x46, 'callproperty')
constructprop = _Avm2CallMN(0x4A, 'constructprop')
callproplex = _Avm2CallMN(0x4C, 'callproplex')
callsupervoid = _Avm2CallMN(0x4E, 'callsupervoid')
callpropvoid = _Avm2CallMN(0x4F, 'callpropvoid')
#}

#{ Instructions that do not chage the stack height stack and take one U30 argument.
astype = _Avm2U30Instruction(0x86, 'astype')
coerce = _Avm2U30Instruction(0x80, 'coerce')
debugfile = _Avm2U30Instruction(0xF1, 'debugfile')
debugline = _Avm2U30Instruction(0xF0, 'debugline')
declocal = _Avm2U30Instruction(0x94, 'declocal')
declocal_i = _Avm2U30Instruction(0xC3, 'declocal_i')
dxns = _Avm2U30Instruction(0x06, 'dxns', flags=METHODFLAG_SetsDxns)
getslot = _Avm2U30Instruction(0x6C, 'getslot')
inclocal = _Avm2U30Instruction(0x92, 'inclocal')
inclocal_i = _Avm2U30Instruction(0xC2, 'inclocal_i')
istype = _Avm2U30Instruction(0xB2, 'istype')
newclass = _Avm2U30Instruction(0x58, 'newclass')
#}

#{ Instructions that push to the stack and take one U30 argument.
getglobalslot = _Avm2U30Instruction(0x6E, 'getglobalslot', 1)
getlex = _Avm2U30Instruction(0x60, 'getlex', 1)
getscopeobject = _Avm2U30Instruction(0x65, 'getscopeobject', 1)
getouterscope = _Avm2U30Instruction(0x67, 'getouterscope', 1)
newcatch = _Avm2U30Instruction(0x5A, 'newcatch', 1)
newfunction = _Avm2U30Instruction(0x40, 'newfunction', 1)
pushdouble = _Avm2U30Instruction(0x2F, 'pushdouble', 1)
pushint = _Avm2U30Instruction(0x2D, 'pushint', 1)
pushnamespace = _Avm2U30Instruction(0x31, 'pushnamespace', 1)
pushshort = _Avm2U30Instruction(0x25, 'pushshort', 1)
pushstring = _Avm2U30Instruction(0x2C, 'pushstring', 1)
pushuint = _Avm2U30Instruction(0x2E, 'pushuint', 1)

getlocal = _Avm2GetLocalInstruction(0x62, 'getlocal')
#}

#{ Instructions that pop from the stack and take one U30 argument.
setlocal = _Avm2SetLocalInstruction(0x63, 'setlocal')
setslot = _Avm2U30Instruction(0x6D, 'setslot', -1)
#}

#{ Instructions that push one value to the stack and take two U30 arguments.
hasnext2 = _Avm2U30Instruction(0x32, 'hasnext2', 1)
#}

#{ Instructions that push/pop values to the stack (depends on arg) and take one U30 argument.
newarray = _Avm2NewArray(0x56, 'newarray')
newobject = _Avm2NewObject(0x55, 'newobject')
#}

#{ Instructions that take one U8 argument.
pushbyte = _Avm2U8Instruction(0x24, 'pushbyte', 1)
#}

#{ Offset instructions
ifeq = _Avm2OffsetInstruction(0x13, 'ifeq', -2)
ifge = _Avm2OffsetInstruction(0x18, 'ifge', -2)
ifgt = _Avm2OffsetInstruction(0x17, 'ifgt', -2)
ifle = _Avm2OffsetInstruction(0x16, 'ifle', -2)
iflt = _Avm2OffsetInstruction(0x15, 'iflt', -2)
ifne = _Avm2OffsetInstruction(0x14, 'ifne', -2)
ifnge = _Avm2OffsetInstruction(0x0F, 'ifnge', -2)
ifngt = _Avm2OffsetInstruction(0x0E, 'ifngt', -2)
ifnle = _Avm2OffsetInstruction(0x0D, 'ifnle', -2)
ifnlt = _Avm2OffsetInstruction(0x0C, 'ifnlt', -2)

ifstricteq = _Avm2OffsetInstruction(0x19, 'ifstricteq', -2)
ifstrictne = _Avm2OffsetInstruction(0x1A, 'ifstrictne', -2)

iffalse = _Avm2OffsetInstruction(0x12, 'iffalse', -1)
iftrue = _Avm2OffsetInstruction(0x11, 'iftrue', -1)

ifjump = _Avm2OffsetInstruction(0x10, 'jump')
#}

#{ Special Instructions
debug = _Avm2DebugInstruction(0xEF, 'debug')

label_internal = _Avm2ShortInstruction(0x09, 'label')
label = _Avm2LabelInstruction(None, 'label');

lookupswitch = _Avm2LookupSwitchInstruction(0x1B, 'lookupswitch')

deleteproperty = _Avm2NamespaceInstruction(0x6A, 'deleteproperty', 1, 1)
getdescendants = _Avm2NamespaceInstruction(0x59, 'getdescendants', 1, 1)
getproperty = _Avm2NamespaceInstruction(0x66, 'getproperty', 1, 1)
getsuper = _Avm2NamespaceInstruction(0x04, 'getsuper', 1, 1)
findproperty = _Avm2NamespaceInstruction(0x5E, 'findproperty', 0, 1)
findpropstrict = _Avm2NamespaceInstruction(0x5D, 'findpropstrict', 0, 1)
initproperty = _Avm2NamespaceInstruction(0x68, 'initproperty', 2, 0)
setproperty = _Avm2NamespaceInstruction(0x61, 'setproperty', 2, 0)
setsuper = _Avm2NamespaceInstruction(0x05, 'setsuper', 2, 0)

kill = _Avm2KillInstruction(0x08, 'kill')
#}
