
# AVM1 = ActionScript Virtual Machine 1
# Used for ActionScript 1 and 2

from pypy.translator.avm.util import BitStream
import struct

class DataTypes(object):
    
    def __init__(self, id, name, size):
        self.id = id
        self.name = name
        self.size = size
        
    def __str__(self):
        return self.name

    def __call__(self, *a, **b):
        pass
    
    __unicode__ = __str__

DataTypes.STRING      = DataTypes(0, "string", "Z")
DataTypes.FLOAT       = DataTypes(1, "float", "f")
DataTypes.NULL        = DataTypes(2, "null", "!")
DataTypes.UNDEFINED   = DataTypes(3, "undefined", "!")
DataTypes.REGISTER    = DataTypes(4, "register", "B")
DataTypes.BOOLEAN     = DataTypes(5, "boolean", "B")
DataTypes.DOUBLE      = DataTypes(6, "double", "d")
DataTypes.INTEGER     = DataTypes(7, "integer", "l")
DataTypes.CONSTANT8   = DataTypes(8, "constant 8", "B")
DataTypes.CONSTANT16  = DataTypes(9, "constant 16", "H")

class Index(object):
    def __init__(self, index):
        self.index = index

class Value(object):
    def __init__(self, value):
        self.value = value

Null = object()
Null.type = DataTypes.Null

Undefined = object()
Undefined.type = DataTypes.UNDEFINED

class Constant(Index):
    def __getattr__(self, name):
        if name == "type":
            if self.index < 256:
                return DataTypes.CONSTANT8
            return DataTypes.CONSTANT16
        return Index.__getattr__(self, name)

class RegisterByIndex(Index):
    type = DataTypes.REGISTER

class RegisterByValue(Value):
    type = DataTypes.REGISTER

class Action(object):
    
    ACTION_NAME = "NotImplemented"
    ACTION_ID = 0x00
    
    def __init__(self):    
        self.offset = 0
        self.label_name = ""
    
    def serialize(self):
        inner_data = self.gen_data()
        outer_data = self.gen_outer_data()
        header = struct.pack("BH", self.ACTION_ID, len(inner_data))
        return bytes + inner_data + outer_data
    
    def __len__(self):
        return 6 + len(self.gen_data()) + len(self.gen_outer_data())
    
    def gen_data(self):
        raise NotImplementedError, "Action::gen_data is not implemented in the abstract class"

    def gen_outer_data(self):
        raise NotImplementedError, "Action::gen_outer_data is not implemented in the abstract class"
    
    def get_block_props_early(self, block):
        raise NotImplementedError, "Action::get_block_props_early is not implemented in the abstract class"

    def get_block_props_late(self, block):
        raise NotImplementedError, "Action::get_block_props_late is not implemented in the abstract class"

class RegisterError(IndexError):
    pass

global_registers = []

class Block(object):

    AUTO_LABEL_TEMPLATE = "label%d"
    MAX_REGISTERS = 4
    FUNCTION_TYPE = 0

    def __init__(self, insert_end=False):
        self.code = ""
        self.__sealed = False
        self.insert_end = insert_end
        
        self.labels = {}
        self.branch_blocks = {}
        self.constants = ActionConstantPool()
        self.actions = [self.constants]
        
        self.current_offset = 0
        self.label_count = 0
        self.registers = global_registers

    def get_free_register(self):
        if None in self.registers:
            return self.registers.index(None)
        elif len(self.registers) < self.MAX_REGISTERS:
            return len(self.registers)
        else:
            raise RegisterError, "maximum number of registers in use"

    def store_register(self, value, index=-1):
        if value in self.registers:
            return self.registers.index(value)
        if index < 1:
            index = self.get_free_register()
        self.registers[index] = value
        return index

    def find_register(self, value):
        if value in self.registers:
            return self.registers.index(value)
        return -1
    
    def free_register(self, index):
        self.registers[index] = None
    
    def __len__(self):
        return self.current_offset + (2 if self.insert_end else 0)

    def seal(self):
        self.__sealed = True
        return len(self)

    def is_sealed(self):
        return self.__sealed
    
    def add_action(self, action):
        if self.__sealed:
            raise Exception, "Block is sealed. Cannot add new actions"
        self.code = "" # Dirty the code.
        action.offset = self.current_offset
        action.get_block_props_early(self)
        
        # Do some early optimizations. Combine two pushes into one.
        if isinstance(action, ActionPush) and isinstance(self.actions[-1], ActionPush):
            old_action = self.actions[-1]
            old_len = len(old_action)
            self.actions[-1].values.extend(action.values)
            self.current_offset += len(old_action) - old_len
            return None

        # Two nots negate. Take them out.
        if isinstance(action, ActionNot) and isinstance(self.actions[-1], ActionNot):
            self.actions.pop()
            self.current_offset -= 1 # len(ShortAction) is 1
            return None
            
        if not isinstance(action, Block): # Don't add block length until we've finalized.
            self.current_offset += len(action)
        
        self.actions.append(action)
        return action
    
    def serialize(self):
        if len(self.code) > 0:
            return self.code
        bytes = []
        for action in self.actions:
            action.get_block_props_late(self)
            bytes += action.serialize()
        if self.insert_end:
            bytes += "\0\0"
        self.code = "".join(bytes)
        return self.code

    def new_label(self):
        self.label_count += 1
        name = Block.AUTO_LABEL_TEMPLATE % self.label_count
        self.labels[name] = -1
        return name
        
    def set_label_here(self, name):
        self.labels[name] = self.current_offset

    def new_label_here(self):
        name = self.new_label()
        self.labels[name] = self.current_offset
        return name

class ActionCall(Action):
    ACTION_NAME = "ActionCall"
    ACTION_ID = 0x9e

class ActionConstantPool(Action):
    ACTION_NAME = "ActionConstantPool"
    ACTION_ID = 0x88

    def __init__(self, *args):
        self.pool = []
        for string in args:
            if not string in self.pool:
                self.pool.append(args)

    def add_constant(self, string):
        if not string in self.pool:
            self.pool.append(string)
            return len(self.pool)-1
        return self.pool.index(string)
    
    def gen_data(self):
        return struct.pack("H", len(self.pool)) + "".join([item + "\0" for item in self.pool])

class ActionDefineFunction(Block, Action):
    ACTION_NAME = "ActionDefineFunction"
    ACTION_ID = 0x9b
    FUNCTION_TYPE = 1

    def __init__(self, name, parameters):
        Block.__init__(self, False)
        self.function_name = name
        self.params = params

    def gen_data(self):
        self.block_data = Block.serialize(self)
        bytes = [self.function_name, "\0", struct.pack("H", len(self.params))]
        bytes += [p + "\0" for p in self.params]
        bytes += struct.pack("H", len(self.block_data))
        return "".join(bytes)

    def gen_outer_data(self):
        return self.block_data

class ActionDefineFunction2(Block, Action):
    ACTION_NAME = "ActionDefineFunction2"
    ACTION_ID = 0x8e
    MAX_REGISTERS = 256
    FUNCTION_TYPE = 2

    def __init__(self, name, parameters, flags=0):
        Block.__init__(self, False)
        self.function_name = name
        self.params = params
        self.flags = flags & 0xFF01
        self.eval_flags()

    def find_register(self):
        if value in self.registers:
            return self.registers.index(value)+1
        return -1
    
    def eval_flags(self): # WARNING! eval_flags will clear registers!
        bits = BitStream()
        bits.write_bit_value(self.flags, 16)
        bits.rewind()
        preload_parent  = bits.read_bit()
        preload_root    = bits.read_bit()
        suppress_super  = bits.read_bit()
        preload_super   = bits.read_bit()
        suppress_args   = bits.read_bit()
        preload_args    = bits.read_bit()
        suppress_this   = bits.read_bit()
        preload_this    = bits.read_bit()
        bits.cursor += 7 # skip over 7 Reserved bits
        preload_global  = bits.read_bit()

        # According to the docs, this is the order of register allocation.
        if preload_this:   self.registers.append("this")
        if preload_args:   self.registers.append("arguments")
        if preload_super:  self.registers.append("super")
        if preload_root:   self.registers.append("_root")
        if preload_parent: self.registers.append("_parent")
        if preload_global: self.registers.append("_global")
        
        for name in self.params:
            self.registers.append(name)
        
    def gen_data(self):
        self.block_data = Block.serialize(self)
        params = [p for p in self.params if isinstance(p, RegisterParam)]
        bytes = [self.function_name, "\0", struct.pack("HBH", len(params), len(self.registers)-1, self.flags)]
        for name in self.params:
            bytes += [chr(self.registers.index(name)+1), name, "\0"]
        
        bytes += [struct.pack("H", len(self.block_data))]
        return "".join(bytes)

    def gen_outer_data(self):
        return self.block_data

class ActionGetURL(Action):
    ACTION_NAME = "ActionGetURL"
    ACTION_ID = 0x83

    def __init__(self, url, target=""):
        self.url = url
        self.target = target

    def gen_data(self):
        return "%s\0%s\0" % (self.url, self.target)

class ActionGetURL2(Action):
    ACTION_NAME = "ActionGetURL2"
    ACTION_ID = 0x9a

    METHOD_NONE = 0
    METHOD_GET  = 1
    METHOD_POST = 2

    def __init__(self, method, load_target=False, load_variables=False):
        self.method = max(method, 2)
        self.load_target = load_target
        self.load_variables = load_varibles

    def gen_data(self):
        bits = BitStream()
        bits.write_bit_value(self.method, 2)
        bits.zero_fill(4)
        bits.write_boolean(load_target)
        bits.write_boolean(load_variables)
        return bits.serialize()

class ActionGotoFrame(Action):
    ACTION_NAME = "ActionGotoFrame"
    ACTION_ID = 0x81

    def __init__(self, index):
        self.index = index

    def gen_data(self):
        return struct.pack("H", self.index)

class ActionGotoFrame2(Action):
    ACTION_NAME = "ActionGotoFrame2"
    ACTION_ID = 0x9f

    def __init__(self, play=False, scene_bias=0):
        self.play = play
        self.scene_bias = scene_bias

    def gen_data(self):
        bits = BitStream()
        bits.zero_fill(6)
        bits.write_boolean(self.scene_bias > 0)
        bits.write_boolean(self.play)

        if self.scene_bias > 0:
            return bits.serialize() + struct.pack("H", sceneBias)

        return bits.serialize()

class ActionGotoLabel(Action):
    ACTION_NAME = "ActionGotoLabel"
    ACTION_ID = 0x81

    def __init__(self, label_name):
        self.label_name = label_name

    def serialize(self):
        return self.label_name + "\0"

class BranchingActionBase(Action):

    def __init__(self, branch):
        if isinstance(branch, str):
            self.branch_label = branch
            self.branch_offset = 0
        elif isinstance(branch, int):
            self.branch_label = None
            self.branch_offset = branch

    def get_block_props_late(self, block):
        if len(self.branch_label) > 0:
            self.branch_offset = block.labels[self.branch_label] - self.offset

    def gen_data(self):
        return struct.pack("H", self.branch_offset)

class ActionJump(BranchingActionBase):
    ACTION_NAME = "ActionJump"
    ACTION_ID = 0x99

class ActionIf(BranchingActionBase):
    ACTION_NAME = "ActionIf"
    ACTION_ID = 0x9d

class ActionPush(Action):
    ACTION_NAME = "ActionPush"
    ACTION_ID = 0x96

    def __init__(self, *args):
        self.values = []
        self.add_element(args)

    def add_element(self, element):
        if isinstance(element, (list, tuple)):
            for el in element:
                self.add_element(el)
        elif hasattr(element, "type"):
            self.values.append((0, type))
        elif isinstance(element, str):
            self.values.append((element, DataTypes.STRING))
        elif isinstance(element, bool):
            self.values.append((element, DataTypes.BOOLEAN))
        elif isinstance(element, int):
            self.values.append((element, DataTypes.INTEGER))
        elif isinstance(element, float):
            if element > 0xFFFFFFFF:
                self.values.append((element, DataTypes.DOUBLE))
            else:
                self.values.append((element, DataTypes.FLOAT))
        elif isinstance(element, Index):
            self.values.append((element.index, element.type))
        elif isinstance(element, RegisterByValue):
            self.values.append((element.value, RegisterByValue))

    def get_block_props_early(self, block):
        for index, (value, type) in enumerate(self.values):
            if type == DataTypes.STRING:
                constant_index = block.constants.add_constant(value)
                self.values[index] = (constant_index, DataTypes.CONSTANT8 if constant_index < 256 else DataTypes.CONSTANT16)
            elif type == RegisterByValue:
                register_index = block.store_register(value)
                self.values[index] = (register_index, DataTypes.REGISTER)
    
    def gen_data(self):
        bytes = []
        for value, type in self.values:
            bytes += chr(type.id)
            if type.size == "Z":
                bytes += [value, "\0"]
            elif type.size != "!":
                bytes += struct.pack(type.size, value)[0]
        return "".join(bytes)

class ActionSetTarget(object):
    ACTION_NAME = "ActionSetTarget"
    ACTION_ID = 0x8b

    def __init__(self, target):
        self.target = target

    def gen_data(self):
        return self.target + "\0"

class ActionStoreRegister(object):
    ACTION_NAME = "ActionStoreRegister"
    ACTION_ID = 0x87

    def __init__(self, index):
        self.index = index

    def gen_data(self):
        return chr(index)

class ActionTry(object):
    ACTION_NAME = "ActionTry"
    ACTION_ID = 0x8f

    def __init__(self, catch_object, try_block=None, catch_block=None, finally_block=None):

        self.catch_object = catch_object
        
        self.try_block = try_block or Block()
        self.catch_block = catch_block or Block()
        self.finally_block = finally_block or Block()

    def gen_data(self):
        has_catch_block = len(self.catch_block.actions) > 0
        bits = BitStream()
        bits.zero_fill(5)
        bits.write_boolean(isinstance(self.catch_object, Register))
        bits.write_boolean(len(self.finally_block.actions) > 0)
        bits.write_boolean(has_catch_block)
        bytes = [bits.serialize()]
        bytes += [struct.pack("HHH", len(self.try_block) + 5 if has_catch_block else 0, len(self.catch_block), len(finallyBlock))]
        bytes += self.catch_object.index if isinstance(self.catch_object, Register) else (self.catch_object + "\0")
        return "".join(bytes)

    def gen_outer_data(self):
        bytes = [self.try_block.serialize()]
        if len(self.catch_block.actions) > 0:
            bytes += ActionJump(len(self.catch_block)).serialize()
            bytes += catchBlock.serialize()
        bytes += self.finally_block.serialize()

class ActionWaitForFrame(Action):
    ACTION_NAME = "ActionWaitForFrame"
    ACTION_ID = 0x8a

    def __init__(self, index, skip_count=0):
        self.index = index
        self.skip_count = skip_count

    def gen_data(self):
        return struct.pack("HB", self.index, self.skip_count)
    
class ActionWaitForFrame2(Action):
    ACTION_NAME = "ActionWaitForFrame2"
    ACTION_ID = 0x8d

    def __init__(self, skip_count=0):
        self.skip_count = skip_count

    def gen_data(self):
        return chr(self.skip_count)

class ActionWith(Action):
    ACTION_NAME = "ActionWith"
    ACTION_ID = 0x94
    
    def __init__(self, with_block):
        self.block = with_block or Block()

    def gen_data(self):
        return struct.pack("H", len(block)) + block.serialize()
    
class ShortAction(Action):
    
    def __call__(self, *args, **kwargs):
        return self
    
    def __init__(self, id, name):
        self.ACTION_ID = id
        self.ACTION_NAME = name
        Action.__init__(self)

    def __len__(self):
        return 1 # 1 (Action ID)

    def serialize(self)
        return chr(self.ACTION_ID)

ActionNextFrame           = ShortAction(0x04, "ActionNextFrame")
ActionPreviousFrame       = ShortAction(0x05, "ActionPreviousFrame")
ActionPlay                = ShortAction(0x06, "ActionPlay")
ActionStop                = ShortAction(0x07, "ActionStop")
ActionToggleQuality       = ShortAction(0x08, "ActionToggleQuality")
ActionStopSounds          = ShortAction(0x09, "ActionStopSounds")
ActionAdd                 = ShortAction(0x0a, "ActionAdd")
ActionSubtract            = ShortAction(0x0b, "ActionSubtract")
ActionMultiply            = ShortAction(0x0c, "ActionMultiply")
ActionDivide              = ShortAction(0x0d, "ActionDivide")
ActionEquals              = ShortAction(0x0e, "ActionEquals")
ActionLess                = ShortAction(0x0f, "ActionLess")
ActionAnd                 = ShortAction(0x10, "ActionAnd")
ActionOr                  = ShortAction(0x11, "ActionOr")
ActionNot                 = ShortAction(0x12, "ActionNot")
ActionStringEquals        = ShortAction(0x13, "ActionStringEquals")
ActionStringLength        = ShortAction(0x14, "ActionStringLength")
ActionStringExtract       = ShortAction(0x15, "ActionStringExtract")
ActionPop                 = ShortAction(0x17, "ActionPop")
ActionToInteger           = ShortAction(0x18, "ActionToInteger")
ActionGetVariable         = ShortAction(0x1c, "ActionGetVariable")
ActionSetVariable         = ShortAction(0x1d, "ActionSetVariable")
ActionSetTarget2          = ShortAction(0x20, "ActionSetTarget2")
ActionStringAdd           = ShortAction(0x21, "ActionStringAdd")
ActionGetProperty         = ShortAction(0x22, "ActionGetProperty")
ActionSetProperty         = ShortAction(0x23, "ActionSetProperty")
ActionCloneSprite         = ShortAction(0x24, "ActionCloneSprite")
ActionRemoveSprite        = ShortAction(0x25, "ActionRemoveSprite")
ActionTrace               = ShortAction(0x26, "ActionTrace")
ActionStartDrag           = ShortAction(0x27, "ActionStartDrag")
ActionEndDrag             = ShortAction(0x28, "ActionEndDrag")
ActionStringLess          = ShortAction(0x29, "ActionStringLess")
ActionThrow               = ShortAction(0x2a, "ActionThrow")
ActionCastOp              = ShortAction(0x2b, "ActionCastOp")
ActionImplementsOp        = ShortAction(0x2c, "ActionImplementsOp")
ActionRandomNumber        = ShortAction(0x30, "ActionRandomNumber")
ActionMBStringLength      = ShortAction(0x31, "ActionMBStringLength")
ActionCharToAscii         = ShortAction(0x32, "ActionCharToAscii")
ActionAsciiToChar         = ShortAction(0x33, "ActionAsciiToChar")
ActionGetTime             = ShortAction(0x34, "ActionGetTime")
ActionMBStringExtract     = ShortAction(0x35, "ActionMBStringExtract")
ActionMBCharToAscii       = ShortAction(0x36, "ActionMBCharToAscii")
ActionMBAsciiToChar       = ShortAction(0x37, "ActionMBAsciiToChar")
ActionDelVar              = ShortAction(0x3a, "ActionDelVar")
ActionDelThreadVars       = ShortAction(0x3b, "ActionDelThreadVars")
ActionDefineLocalVal      = ShortAction(0x3c, "ActionDefineLocalVal")
ActionCallFunction        = ShortAction(0x3d, "ActionCallFunction")
ActionReturn              = ShortAction(0x3e, "ActionReturn")
ActionModulo              = ShortAction(0x3f, "ActionModulo")
ActionNewObject           = ShortAction(0x40, "ActionNewObject")
ActionDefineLocal         = ShortAction(0x41, "ActionDefineLocal")
ActionInitArray           = ShortAction(0x42, "ActionInitArray")
ActionInitObject          = ShortAction(0x43, "ActionInitObject")
ActionTypeof              = ShortAction(0x44, "ActionTypeof")
ActionGetTargetPath       = ShortAction(0x45, "ActionGetTargetPath")
ActionEnumerate           = ShortAction(0x46, "ActionEnumerate")
ActionTypedAdd            = ShortAction(0x47, "ActionTypedAdd")
ActionTypedLessThan       = ShortAction(0x48, "ActionTypedLessThan")
ActionTypedEquals         = ShortAction(0x49, "ActionTypedEquals")
ActionConvertToNumber     = ShortAction(0x4a, "ActionConvertToNumber")
ActionConvertToString     = ShortAction(0x4b, "ActionConvertToString")
ActionDuplicate           = ShortAction(0x4c, "ActionDuplicate")
ActionSwap                = ShortAction(0x4d, "ActionSwap")
ActionGetMember           = ShortAction(0x4e, "ActionGetMember")
ActionSetMember           = ShortAction(0x4f, "ActionSetMember")
ActionIncrement           = ShortAction(0x50, "ActionIncrement")
ActionDecrement           = ShortAction(0x51, "ActionDecrement")
ActionCallMethod          = ShortAction(0x52, "ActionCallMethod")
ActionCallNewMethod       = ShortAction(0x53, "ActionCallNewMethod")
ActionBitAnd              = ShortAction(0x60, "ActionBitAnd")
ActionBitOr               = ShortAction(0x61, "ActionBitOr")
ActionBitXor              = ShortAction(0x62, "ActionBitXor")
ActionShiftLeft           = ShortAction(0x63, "ActionShiftLeft")
ActionShiftRight          = ShortAction(0x64, "ActionShiftRight")
ActionShiftUnsigned       = ShortAction(0x65, "ActionShiftUnsigned")
ActionStrictEquals        = ShortAction(0x66, "ActionStrictEquals")
ActionGreater             = ShortAction(0x67, "ActionGreater")
ActionStringGreater       = ShortAction(0x68, "ActionStringGreater")
ActionExtends             = ShortAction(0x69, "ActionExtends")
