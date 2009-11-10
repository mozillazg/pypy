
import struct

from pypy.translator.avm2.constants import AbcConstantPool, METHODFLAG_HasOptional, METHODFLAG_HasParamNames, py_to_abc
from pypy.translator.avm1.util import BitStream
from pypy.translator.avm2.util import serialize_u32 as u32, ValuePool

MAJOR_VERSION = 46
MINOR_VERSION = 16

class AbcFile(object):

    write_to = "abc"
    
    def __init__(self, constants=None):
        self.constants = constants or AbcConstantPool()
        self.methods   = ValuePool(parent=self)
        self.metadatas = ValuePool(parent=self)
        self.instances = ValuePool(parent=self)
        self.classes   = ValuePool(parent=self)
        self.scripts   = ValuePool(parent=self)
        self.bodies    = ValuePool(parent=self)

    def write(self, value):
        if hasattr(value, "write_to_abc"):
            value.write_to_abc(self)
        if hasattr(value, "write_to_pool"):
            value.write_to_pool(self.constants)

    def serialize(self):
        def write_pool(pool, prefix_count=True):
            code = ""
            if prefix_count:
                code += u32(len(pool))
            for item in pool:
                code += item.serialize()
            return code
        
        code = ""
        code += struct.pack("<HH", MINOR_VERSION, MAJOR_VERSION)
        code += self.constants.serialize()
        
        code += write_pool(self.methods)
        code += write_pool(self.metadatas)
        code += write_pool(self.instances)
        code += write_pool(self.classes, False)
        code += write_pool(self.scripts)
        code += write_pool(self.bodies)

        return code

class AbcMethodInfo(object):

    def __init__(self, name, param_types, return_type, flags=0, options=None, param_names=None):
        self.name = name
        self._name_index = None
        
        self.param_types = param_types
        self._param_types_indices = None

        self.param_names = param_names
        self._param_names_indices = None
        
        self.return_type = return_type
        self._return_type_index = None
        
        self.flags = flags
        
        self.options = options
        self._options_indices = None

    def serialize(self):
        code = ""

        code += u32(len(self.param_types))
        code += u32(self._return_type_index)
        
        code += ''.join(u32(index) for index in self._param_types_indices)
        code += u32(self._name_index)

        if self.options:
            self.flags |= METHODFLAG_HasOptional
            
        if self.param_names:
            self.flags |= METHODFLAG_HasParamNames

        code += chr(self.flags & 0xFF)

        if self.options:
            code += u32(len(self.options))
            for ctype, index in self._options_indices:
                code += u32(index)
                code += chr(ctype)

        if self.param_names:
            code += ''.join(u32(index) for index in self._param_names_indices)

        return code

    def write_to_pool(self, pool):
        self._name_index = pool.utf8_pool.index_for(self.name)
        self._return_type_index = pool.multiname_pool.index_for(self.return_type)

        if self.param_types:
            self._param_types_indices = [pool.multiname_pool.index_for(i) for i in self.param_types]
        else:
            self._param_types_indices = []
        
        if self.param_names:
            self._param_names_indices = [pool.utf8_pool.index_for(i) for i in self.param_names]
        else:
            self._param_names_indices = []

        if self.options:
            self._options_indices = [py_to_abc(value) for value in self.options]
            

class AbcMetadataInfo(object):

    def __init__(self, name, items):
        self.name = name
        self._name_index = None
        
        self.items = items
        self._items_indices = None
        
    def serialize(self):
        code = ""
        code += u32(self._name_index)
        code += u32(len(self.items))

        for key_i, val_i in self._items_indices:
            code += u32(key_i)
            code += u32(val_i)
        
        return code

    def write_to_pool(self, pool):
        strindex = pool.utf8_pool.index_for
        self._name_index = strindex(self.name)
        self._items_indices = [(strindex(k), strindex(v)) for k, v in self.items.iteritems()]

class AbcInstanceInfo(object):
    def __init__(self, name, iinit, interfaces=None,
                 is_interface=False, final=False, sealed=True,
                 super_name=None, traits=None, protectedNs=None):
        self.name = name
        self._name_index = None

        self.super_name = super_name
        self._super_name_index = None

        self.is_interface = is_interface
        self.is_sealed = sealed
        self.is_final = final

        self.interfaces = interfaces or []
        self._interface_indices = None
        
        self.iinit = iinit
        self._iinit_index = 0

        self.traits = traits or []

        self.protectedNs = protectedNs
        self._protectedNs_index = None
        
    def serialize(self):

        code = ""
        code += u32(self._name_index)
        code += u32(self._super_name_index)

        # Flags
        flags = BitStream()
        flags.zero_fill(4)                        # first four bits = not defined
        flags.write_bit(self.protectedNs != None) # 1000 = 0x08 = CLASSFLAG_ClassProtectedNs
        flags.write_bit(self.is_interface)        # 0100 = 0x04 = CLASSFLAG_ClassInterface
        flags.write_bit(self.is_final)            # 0010 = 0x02 = CLASSFLAG_ClassFinal
        flags.write_bit(self.is_sealed)           # 0001 = 0x01 = CLASSFLAG_ClassSealed

        code += flags.serialize()

        if self.protectedNs:
            code += u32(self._protectedNs_index)

        code += u32(len(self.interfaces))
        for index in self._interface_indices:
            code += u32(index)
            
        code += u32(self._iinit_index)
        
        code += u32(len(self.traits))
        for trait in self.traits:
            code += trait.serialize()

        return code

    def write_to_pool(self, pool):
        self._name_index = pool.multiname_pool.index_for(self.name)
        self._super_name_index = pool.multiname_pool.index_for(self.super_name)
        self._interface_indices = [pool.multiname_pool.index_for(i) for i in self.interfaces]

        if self.protectedNs:
            self._protectedNs_index = pool.namespace_pool.index_for(self.protectedNs)

        for trait in self.traits:
            trait.write_to_pool(pool)

    def write_to_abc(self, abc):
        self._iinit_index = abc.methods.index_for(self.iinit)
        
        for trait in self.traits:
            trait.write_to_abc(abc)

class AbcClassInfo(object):
    def __init__(self, cinit, traits=None):
        self.traits = traits or []
        
        self.cinit = cinit
        self._cinit_index = None

    def serialize(self):
        
        code = ""
        
        code += u32(self._cinit_index)
        code += u32(len(self.traits))
        for trait in self.traits:
            code += trait.serialize()

        return code
    
    def write_to_abc(self, abc):
        self._cinit_index = abc.methods.index_for(self.cinit)
        for trait in self.traits:
            trait.write_to_abc(abc)

    def write_to_pool(self, pool):
        for trait in self.traits:
            trait.write_to_pool(pool)

class AbcScriptInfo(object):
    def __init__(self, init, traits=None):
        self.traits = traits or []
        
        self.init = init
        self._init_index = None

    def serialize(self):
        
        code = ""
        
        code += u32(self._init_index)
        code += u32(len(self.traits))
        for trait in self.traits:
            code += trait.serialize()

        return code
    
    def write_to_abc(self, abc):
        self._init_index = abc.methods.index_for(self.init)
        for trait in self.traits:
            trait.write_to_abc(abc)

    def write_to_pool(self, pool):
        for trait in self.traits:
            trait.write_to_pool(pool)

class AbcMethodBodyInfo(object):

    def __init__(self, method_info, code, traits=None, exceptions=None):
        self.method_info = method_info
        self._method_info_index = None

        self.code = code
        
        self.traits = traits or []
        self.exceptions = exceptions or []

    def serialize(self):
        code = ""
        code += u32(self._method_info_index)
        code += u32(self.code._stack_depth_max)
        code += u32(len(self.code.temporaries))
        code += u32(0) # FIXME: For now, init_scope_depth is always 0.
        code += u32(self.code._scope_depth_max)
        code += u32(len(self.code))
        code += self.code.serialize()

        code += u32(len(self.exceptions))
        for exc in self.exceptions:
            code += exc.serialize()

        code += u32(len(self.traits))
        for trait in self.traits:
            code += trait.serialize()

        return code

    def write_to_abc(self, abc):
        self._method_info_index = abc.methods.index_for(self.method_info)
        for trait in self.traits:
            trait.write_to_abc(abc)

    def write_to_pool(self, pool):
        for trait in self.traits:
            trait.write_to_pool(pool)

class AbcException(object):
    def __init__(self, from_, to_, target, exc_type, var_name):
        self.from_ = from_
        self.to_ = to_
        self.target = target
        
        self.exc_type = exc_type
        self._exc_type_index = None

        self.var_name = var_name
        self._var_name_index = None

    def serialize(self):
        code = ""
        code += u32(self.from_)
        code += u32(self.to_)
        code += u32(self.target)
        code += u32(self._exc_type_index)
        code += u32(self._var_name_index)
        return code

    def write_to_pool(self, pool):
        self._exc_type_index = pool.utf8_pool.index_for(self.exc_type)
        self._var_name_index = pool.utf8_pool.index_for(self.var_name)
        
        
