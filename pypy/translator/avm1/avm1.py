
# AVM1 = ActionScript Virtual Machine 1
# Used for ActionScript 1 and 2

from pypy.translator.avm1.util import BitStream
from collections import namedtuple
import struct

DataType = namedtuple("DataType", "id name size")

STRING      = DataType(0, "string", "Z")
FLOAT       = DataType(1, "float", "f")
NULL        = DataType(2, "null", "!")
UNDEFINED   = DataType(3, "undefined", "!")
REGISTER    = DataType(4, "register", "B")
BOOLEAN     = DataType(5, "boolean", "B")
DOUBLE      = DataType(6, "double", "d")
INTEGER     = DataType(7, "integer", "l")
CONSTANT8   = DataType(8, "constant 8", "B")
CONSTANT16  = DataType(9, "constant 16", "H")

preload = dict(this="preload_this",
               arguments="preload_args",
               super="preload_super",
               _root="preload_root",
               _parent="preload_parent",
               _global="preload_global")

class Action(object):
    
    ACTION_NAME = "NotImplemented"
    ACTION_ID = 0x00

    offset = 0
    label_name = ""
    
    def serialize(self):
        inner_data = self.gen_data()
        outer_data = self.gen_outer_data()
        header = struct.pack("<BH", self.ACTION_ID, len(inner_data))
        return header + inner_data + outer_data
    
    def __len__(self):
        return 6 + len(self.gen_data()) + len(self.gen_outer_data())
    
    def gen_data(self):
        return ""

    def gen_outer_data(self):
        return ""
    
    def get_block_props_early(self, block):
        pass

    def get_block_props_late(self, block):
        pass

class RegisterError(IndexError):
    pass

class SealedBlockError(Exception):
    pass

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

    def serialize(self):
        if len(self.pool) == 0:
            return ""
        else:
            return super(ActionConstantPool, self).serialize()
    
    def gen_data(self):
        return struct.pack("H", len(self.pool)) + "\0".join(self.pool) + "\0"

class Block(object):

    AUTO_LABEL_TEMPLATE = "label%d"
    MAX_REGISTERS = 4
    FUNCTION_TYPE = 0
    
    def __init__(self, toplevel, insert_end=False):
        if toplevel:
            self.constants = toplevel.constants
            self.registers = toplevel.registers
        else:
            self.constants = ActionConstantPool()
            self.registers = []
        
        self.code = ""
        self._sealed = False
        self.insert_end = insert_end
        
        self.labels = {}
        self.branch_blocks = []
        self.actions = []
        
        self.current_offset = 0
        self.label_count = 0
    
    def get_free_register(self):
        if None in self.registers:
            return self.registers.index(None)
        elif len(self.registers) < self.MAX_REGISTERS:
            self.registers.append(None)
            return len(self.registers)-1
        else:
            raise RegisterError("maximum number of registers in use")

    def store_register(self, value, index=-1):
        if value in self.registers:
            index = self.registers.index(value)
            return index
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
        self._sealed = True
        return len(self)

    @property
    def sealed(self):
        return self._sealed
    
    def add_action(self, action):
        if self._sealed:
            raise SealedBlockError("Block is sealed. Cannot add new actions")

        assert isinstance(action, Action)
        
        self.code = "" # Dirty the code.
        action.offset = self.current_offset
        action.get_block_props_early(self)
        
        # Do some early optimizations. Combine two pushes into one.
        if len(self.actions) > 0 and action.ACTION_NAME == "ActionPush" and self.actions[-1].ACTION_NAME == "ActionPush":
            old_action = self.actions[-1]
            old_len = len(old_action)
            self.actions[-1].values.extend(action.values)
            self.current_offset += len(old_action) - old_len
            return old_action

        # Two nots negate. Take them out.
        if len(self.actions) > 0 and action.ACTION_NAME == "ActionNot" and self.actions[-1].ACTION_NAME == "ActionNot":
            self.actions.pop()
            self.current_offset -= 1 # len(ShortAction) is 1
            return None
            
        if not isinstance(action, Block): # Don't add block length until we've finalized.
            self.current_offset += len(action)
        
        self.actions.append(action)
        return action
    
    def serialize(self):
        if not self._sealed:
            raise SealedBlockError("Block must be sealed before it can be serialized")
        if len(self.code) > 0:
            return self.code
        bytes = []
        block_offset = 0
        for action in self.actions:
            if isinstance(action, Block):
                block_offset += len(action)
            action.offset += block_offset
            action.get_block_props_late(self)
            bytes += action.serialize()
        if self.insert_end:
            bytes += "\0"
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

class ActionDefineFunction(Action, Block):
    ACTION_NAME = "ActionDefineFunction"
    ACTION_ID = 0x9b
    FUNCTION_TYPE = 1

    def __init__(self, toplevel, name, parameters):
        Block.__init__(self, toplevel, False)
        self.function_name = name
        self.params = parameters

    def gen_data(self):
        self.block_data = Block.serialize(self)
        bytes = [self.function_name, "\0", struct.pack("H", len(self.params))]
        bytes += [p + "\0" for p in self.params]
        bytes += struct.pack("H", len(self.block_data))
        return "".join(bytes)

    def gen_outer_data(self):
        return self.block_data

class ActionDefineFunction2(Action, Block):
    ACTION_NAME = "ActionDefineFunction2"
    ACTION_ID = 0x8e
    MAX_REGISTERS = 256
    FUNCTION_TYPE = 2

    def __init__(self, toplevel, name, parameters):
        Block.__init__(self, toplevel, False)
        self.function_name = name
        self.params = parameters
        self.preload_register_count = 1 # Start at 1.
        
        # Flags
        self.registers        = [None]
        self.preload_parent   = False
        self.preload_root     = False
        self.suppress_super   = True
        self.preload_super    = False
        self.suppress_args    = True
        self.preload_args     = False
        self.suppress_this    = True
        self.preload_this     = False
        self.preload_global   = False
        self.eval_flags()

        for name in parameters:
            self.registers.append(name)
        
    def eval_flags(self):
        
        # According to the docs, this is the order of register allocation.
        if self.preload_this and "this" not in self.registers:
            self.suppress_this = False
            self.registers.insert(1, "this")
            
        if self.preload_args and "arguments" not in self.registers:
            self.suppress_args = False
            self.registers.insert(2, "arguments")
            
        if self.preload_super and "super" not in self.registers:
            self.suppress_super = False
            self.registers.insert(3, "super")
            
        if self.preload_root and "_root" not in self.registers:
            self.registers.insert(4, "_root")
            
        if self.preload_parent and "_parent" not in self.registers:
            self.registers.insert(5, "_parent")
        
        if self.preload_global and "_global" not in self.registers:
            self.registers.insert(6, "_global")
        
    def gen_data(self):

        bits = BitStream()
        bits.write_bit(self.preload_parent)
        bits.write_bit(self.preload_root)
        bits.write_bit(self.suppress_super)
        bits.write_bit(self.preload_super)
        bits.write_bit(self.suppress_args)
        bits.write_bit(self.preload_args)
        bits.write_bit(self.suppress_this)
        bits.write_bit(self.preload_this)
        bits.zero_fill(7) # skip over 7 Reserved bits
        bits.write_bit(self.preload_global)
        
        self.block_data = Block.serialize(self)
        bytes = [self.function_name, "\0",
                 struct.pack("HB", len(self.params), len(self.registers)),
                 bits.serialize()]
        
        for name in self.params:
            bytes += [chr(self.registers.index(name)), name, "\0"]
        
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

    METHODS = {"": 0, "GET": 1, "POST": 2}

    def __init__(self, method, load_target=False, load_variables=False):
        self.method = method
        self.load_target = load_target
        self.load_variables = load_variables

    def gen_data(self):
        # The SWF 10 spec document is incorrect.
        # method goes at the low end
        # and the flags at the high end
        bits = BitStream()
        bits.write_bit(self.load_variables)
        bits.write_bit(self.load_target)
        bits.zero_fill(4)
        bits.write_int_value(self.METHODS[self.method.upper()], 2)
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
        bits.write_bit(self.scene_bias > 0)
        bits.write_bit(self.play)

        if self.scene_bias > 0:
            return bits.serialize() + struct.pack("<H", self.scene_bias)

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
            print "BRANCH:", self.branch_label, block.labels[self.branch_label], self.offset
            self.branch_offset = block.labels[self.branch_label] - self.offset - len(self)

    def gen_data(self):
        return struct.pack("h", self.branch_offset)

class ActionJump(BranchingActionBase):
    ACTION_NAME = "ActionJump"
    ACTION_ID = 0x99

class ActionIf(BranchingActionBase):
    ACTION_NAME = "ActionIf"
    ACTION_ID = 0x9d

class ActionPush(Action):
    ACTION_NAME = "ActionPush"
    ACTION_ID = 0x96

    USE_CONSTANTS = False
    
    def __init__(self, *args):
        self.values = []
        self.add_element(*args)
    
    def add_element(self, element):
        if hasattr(element, "__iter__") and not isinstance(element, (basestring, tuple)):
            for t in element:
                self.add_element(t)
        else:
            if element in (NULL, UNDEFINED):
                element = (None, element)
            assert isinstance(element, tuple)
            self.values.append(element)
        
    def get_block_props_early(self, block):
        if not ActionPush.USE_CONSTANTS: return
        for index, (value, type) in enumerate(self.values):
            if type == STRING:
                constant_index = block.constants.add_constant(value)
                self.values[index] = (constant_index, CONSTANT8 if constant_index < 256 else CONSTANT16)
    
    def gen_data(self):
        bytes = []
        for value, type in self.values:
            bytes += chr(type.id)
            if type.size == "Z":
                bytes += [value, "\0"]
            elif type.size != "!":
                bytes += struct.pack("<"+type.size, value)
        return "".join(bytes)

class ActionSetTarget(Action):
    ACTION_NAME = "ActionSetTarget"
    ACTION_ID = 0x8b

    def __init__(self, target):
        self.target = target

    def gen_data(self):
        return self.target + "\0"

class ActionStoreRegister(Action):
    ACTION_NAME = "ActionStoreRegister"
    ACTION_ID = 0x87

    def __init__(self, index):
        self.index = index

    def gen_data(self):
        return chr(self.index)

class ActionTry(Action):
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
        bits.write_bit(isinstance(self.catch_object, int))
        bits.write_bit(len(self.finally_block.actions) > 0)
        bits.write_bit(has_catch_block)
        bytes = [bits.serialize()]
        bytes += [struct.pack("3H",
                              len(self.try_block) + 5 if has_catch_block else 0,
                              len(self.catch_block),
                              len(self.finally_block))]
        bytes += [self.catch_object, "" if isinstance(self.catch_object, int) else "\0"]
        return bytes

    def gen_outer_data(self):
        bytes = [self.try_block.serialize()]
        if len(self.catch_block.actions) > 0:
            bytes += ActionJump(len(self.catch_block)).serialize()
            bytes += self.catch_block.serialize()
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
        return struct.pack("H", len(self.block)) + self.block.serialize()

SHORT_ACTIONS = {}

# turns NextFrame into next_frame
def make_underlined(name):
    return ''.join('_' + c.lower() if c.isupper() else c for c in name)[1:]

def make_short_action(value, name, push_count=0):
    
    def __len__(self):
        return 1 # 1 (Action ID)
    
    def serialize(self):
        return chr(self.ACTION_ID)
    
    act = type(name, (Action,), dict(ACTION_ID=value, ACTION_NAME=name, push_count=push_count,
                                     __len__=__len__, serialize=serialize))

    SHORT_ACTIONS[name[6:].lower()] = act
    SHORT_ACTIONS[make_underlined(name[6:])] = act

    return act

ActionNextFrame           = make_short_action(0x04, "ActionNextFrame")
ActionPreviousFrame       = make_short_action(0x05, "ActionPreviousFrame")
ActionPlay                = make_short_action(0x06, "ActionPlay")
ActionStop                = make_short_action(0x07, "ActionStop")
ActionToggleQuality       = make_short_action(0x08, "ActionToggleQuality")
ActionStopSounds          = make_short_action(0x09, "ActionStopSounds")
ActionAdd                 = make_short_action(0x0a, "ActionAdd", -1)
ActionSubtract            = make_short_action(0x0b, "ActionSubtract", -1)
ActionMultiply            = make_short_action(0x0c, "ActionMultiply", -1)
ActionDivide              = make_short_action(0x0d, "ActionDivide", -1)
ActionEquals              = make_short_action(0x0e, "ActionEquals", -1)
ActionLess                = make_short_action(0x0f, "ActionLess", -1)
ActionAnd                 = make_short_action(0x10, "ActionAnd", -1)
ActionOr                  = make_short_action(0x11, "ActionOr", -1)
ActionNot                 = make_short_action(0x12, "ActionNot")
ActionStringEquals        = make_short_action(0x13, "ActionStringEquals", -1)
ActionStringLength        = make_short_action(0x14, "ActionStringLength")
ActionStringExtract       = make_short_action(0x15, "ActionStringExtract")
ActionPop                 = make_short_action(0x17, "ActionPop", -1)
ActionToInteger           = make_short_action(0x18, "ActionToInteger")
ActionGetVariable         = make_short_action(0x1c, "ActionGetVariable")
ActionSetVariable         = make_short_action(0x1d, "ActionSetVariable", -2)
ActionSetTarget2          = make_short_action(0x20, "ActionSetTarget2")
ActionStringAdd           = make_short_action(0x21, "ActionStringAdd", -1)
ActionGetProperty         = make_short_action(0x22, "ActionGetProperty", -1)
ActionSetProperty         = make_short_action(0x23, "ActionSetProperty", -3)
ActionCloneSprite         = make_short_action(0x24, "ActionCloneSprite")
ActionRemoveSprite        = make_short_action(0x25, "ActionRemoveSprite")
ActionTrace               = make_short_action(0x26, "ActionTrace", -1)
ActionStartDrag           = make_short_action(0x27, "ActionStartDrag")
ActionEndDrag             = make_short_action(0x28, "ActionEndDrag")
ActionStringLess          = make_short_action(0x29, "ActionStringLess")
ActionThrow               = make_short_action(0x2a, "ActionThrow")
ActionCastOp              = make_short_action(0x2b, "ActionCastOp")
ActionImplementsOp        = make_short_action(0x2c, "ActionImplementsOp")
ActionRandomNumber        = make_short_action(0x30, "ActionRandomNumber")
ActionMBStringLength      = make_short_action(0x31, "ActionMBStringLength")
ActionCharToAscii         = make_short_action(0x32, "ActionCharToAscii")
ActionAsciiToChar         = make_short_action(0x33, "ActionAsciiToChar")
ActionGetTime             = make_short_action(0x34, "ActionGetTime")
ActionMBStringExtract     = make_short_action(0x35, "ActionMBStringExtract")
ActionMBCharToAscii       = make_short_action(0x36, "ActionMBCharToAscii")
ActionMBAsciiToChar       = make_short_action(0x37, "ActionMBAsciiToChar")
ActionDelVar              = make_short_action(0x3a, "ActionDelVar")
ActionDelThreadVars       = make_short_action(0x3b, "ActionDelThreadVars")
ActionDefineLocalVal      = make_short_action(0x3c, "ActionDefineLocalVal")
ActionCallFunction        = make_short_action(0x3d, "ActionCallFunction")
ActionReturn              = make_short_action(0x3e, "ActionReturn")
ActionModulo              = make_short_action(0x3f, "ActionModulo", -1)
ActionNewObject           = make_short_action(0x40, "ActionNewObject")
ActionDefineLocal         = make_short_action(0x41, "ActionDefineLocal")
ActionInitArray           = make_short_action(0x42, "ActionInitArray")
ActionInitObject          = make_short_action(0x43, "ActionInitObject")
ActionTypeof              = make_short_action(0x44, "ActionTypeof")
ActionGetTargetPath       = make_short_action(0x45, "ActionGetTargetPath")
ActionEnumerate           = make_short_action(0x46, "ActionEnumerate")
ActionTypedAdd            = make_short_action(0x47, "ActionTypedAdd", -1)
ActionTypedLess           = make_short_action(0x48, "ActionTypedLess", -1)
ActionTypedEquals         = make_short_action(0x49, "ActionTypedEquals", -1)
ActionConvertToNumber     = make_short_action(0x4a, "ActionConvertToNumber")
ActionConvertToString     = make_short_action(0x4b, "ActionConvertToString")
ActionDuplicate           = make_short_action(0x4c, "ActionDuplicate", 1)
ActionSwap                = make_short_action(0x4d, "ActionSwap")
ActionGetMember           = make_short_action(0x4e, "ActionGetMember", -1)
ActionSetMember           = make_short_action(0x4f, "ActionSetMember", -3)
ActionIncrement           = make_short_action(0x50, "ActionIncrement")
ActionDecrement           = make_short_action(0x51, "ActionDecrement")
ActionCallMethod          = make_short_action(0x52, "ActionCallMethod")
ActionCallNewMethod       = make_short_action(0x53, "ActionCallNewMethod")
ActionBitAnd              = make_short_action(0x60, "ActionBitAnd", -1)
ActionBitOr               = make_short_action(0x61, "ActionBitOr", -1)
ActionBitXor              = make_short_action(0x62, "ActionBitXor", -1)
ActionShiftLeft           = make_short_action(0x63, "ActionShiftLeft", -1)
ActionShiftRight          = make_short_action(0x64, "ActionShiftRight", -1)
ActionShiftUnsigned       = make_short_action(0x65, "ActionShiftUnsigned", -1)
ActionStrictEquals        = make_short_action(0x66, "ActionStrictEquals", -1)
ActionGreater             = make_short_action(0x67, "ActionGreater", -1)
ActionStringGreater       = make_short_action(0x68, "ActionStringGreater", -1)
ActionExtends             = make_short_action(0x69, "ActionExtends")
