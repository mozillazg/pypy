
import struct

from pypy.translator.avm2.constants import AbcConstantPool, ValuePool, METHODFLAG_HasOptional, METHODFLAG_HasParamNames, py_to_abc, QName
from pypy.translator.avm2.util import serialize_u32 as u32
from pypy.translator.avm1.util import BitStream

TRAIT_Slot     = 0
TRAIT_Method   = 1
TRAIT_Getter   = 2
TRAIT_Setter   = 3
TRAIT_Class    = 4
TRAIT_Function = 5
TRAIT_Const    = 6

class AbcTrait(object):
    KIND = None
    def __init__(self, name, final=False, override=False):
        self.name = name
        self._name_index = None

        self.is_final = final
        self.is_override = override

        self.metadata = []
        self._metadata_indices = None

    def write_to_file(self, abc):
        self._metadata_indices = [abc.metadatas.index_for(m) for m in self.metadata]

    def write_to_pool(self, pool):
        self._name_index = pool.multiname_pool.index_for(self.name)

    @property
    def data(self):
        return ""
        
    def serialize(self):
        
        code = ""

        code += u32(self._name_index)

        flags = BitStream()
        flags.write_bit(False)
        flags.write_bit(bool(self.metadata)) # ATTR_Metadata
        flags.write_bit(self.is_override)    # ATTR_Override
        flags.write_bit(self.is_final)       # ATTR_Final
        
	flags.write_int_value(self.KIND, 4)  # kind

        code += flags.serialize()

        code += self.data
        
        if self.metadata:
            code += u32(len(self.metadata))
            for m in self._metadata_indices:
                code += u32(m)

        return code

class AbcClassTrait(object):
    KIND = TRAIT_Class

    def __init__(self, name, cls, slot_id=0, final=False, override=False):
        super(AbcClassTrait, self).__init__(name, final, override)
        self.slot_id = slot_id
        self.cls = cls
        self._class_index = None

    def write_to_file(self, abc):
        super(AbcClassTrait, self).write_to_file(abc)
        self._class_index = abc.classes.index_for(self.cls)

    @property
    def data(self):
        return u32(self.slot_id) + u32(self._class_index)

class AbcSlotTrait(object):
    KIND = TRAIT_Slot

    def __init__(self, name, type_name, value=None, slot_id=0):
        super(AbcSlotTrait, self).__init__(name, False, False)
        self.slot_id = slot_id
        
        self.type_name = type_name
        self._type_name_index = None
        
        self.value = value
        self._value_index = None
        self._value_kind  = None

    def write_to_pool(self, pool):
        super(AbcSlotTrait, self).write_to_pool(pool)
        if self.value is not None:
            self._value_kind, p = py_to_abc(self.value)
            if p is not None:
                self._value_index = p.index_for(self.value)
            else:
                self._value_index = self._value_kind
        
        self._type_name_index = pool.multiname_pool.index_for(self.type_name)

    @property
    def data(self):
        
        code = ""
        
        code += u32(self.slot_id)
        code += u32(self._type_nameIndex)
        code += u32(self._value_index)
        if self._value_index:
            code += u32(self._value_kind)

        return code
        
class AbcConstTrait(AbcSlotTrait):
    KIND = TRAIT_Const

class AbcFunctionTrait(AbcTrait):
    KIND = TRAIT_Function
    def __init__(self, name, function, slot_id=0):
        super(AbcFunctionTrait, self).__init__(name, False, False)
        self.slot_id = slot_id
        
        self.function = function
        self._function_index = None

    def write_to_file(self, abc):
        super(AbcFunctionTrait, self).write_to_file(abc)
        self._function_index = abc.methods.index_for(func)

    @property
    def data(self):
        return u32(self.slot_id) + u32(self._function_index)

class AbcMethodTrait(AbcTrait):
    KIND = TRAIT_Method
    def __init__(self, method, disp_id, final=False, override=False):
        super(AbcMethodTrait, self).__init__(name, final, override)
        self.disp_id = disp_id
        
        self.method = method
        self._method_index = None

    def write_to_file(self, abc):
        super(AbcMethodTrait, self).write_to_file(abc)
        self._method_index = abc.methods.index_for(self.method)

    @property
    def data(self):
        return u32(self.disp_id) + u32(self._method_index)
    
class AbcGetterTrait(AbcMethodTrait):
    KIND = TRAIT_Getter

class AbcSetterTrait(AbcMethodTrait):
    KIND = TRAIT_Setter
