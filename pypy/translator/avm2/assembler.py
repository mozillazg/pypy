
from collections import namedtuple
from pypy.translator.avm2.util import Avm2Backpatch, Avm2Label, serialize_s24 as s24, ValuePool, replace_substr

class BackpatchNotSealed(Exception):
    def __init__(self, b):
        self.backpatch = b
    
    def __str__(self):
        return "Backpatch not sealed: %s" % (self.backpatch,)
        

class Avm2CodeAssembler(object):
    
    def __init__(self, constants, local_names):
        self.temporaries = ValuePool()
        for i in local_names:
            self.temporaries.index_for(i)
        
        self._stack_depth = 0
        self._scope_depth = 0

        self._stack_depth_max = 0
        self._scope_depth_max = 0

        self.code = ""
        self.backpatches = []
        self.labels = {}

        self.flags = 0
        self.constants = constants

    def add_instruction(self, instruction):
        instruction.set_assembler_props(self)
        self.code += instruction.serialize()
        
    def add_instructions(self, instructions):
        for i in instructions:
            self.add_instruction(i)
    
    add = add_instructions
    
    @property
    def stack_depth(self):
        return self._stack_depth

    @stack_depth.setter
    def stack_depth(self, value):
        self._stack_depth = value
        self._stack_depth_max = max(value, self._stack_depth_max)

    @property
    def scope_depth(self):
        return self._scope_depth

    @scope_depth.setter
    def scope_depth(self, value):
        self._scope_depth = value
        self._scope_depth_max = max(value, self._scope_depth_max)
        
    @property
    def next_free_local(self):
        return self.temporaries.next_free()

    def set_local(self, name):
        return self.temporaries.index_for(name, True)

    def get_local(self, name):
        return self.temporaries.index_for(name, False)
    
    def kill_local(self, name):
        return self.temporaries.kill(name)

    def has_local(self, name):
        return name in self.temporaries

    @property
    def local_count(self):
        return len(self.temporaries)
    
    def add_backpatch(self, bkptch):
        self.backpatches.append(bkptch)

    def seal_backpatches(self):
        for b in self.backpatches:
            if b.lbl.address == None:
                raise BackpatchNotSealed(b)
            v = b.lbl.address - b.base
            l = b.location
            self.code = replace_substr(self.code, s24(v), l, l+3)
            
        self.backpatches = []

    def serialize(self):
        self.seal_backpatches()
        return self.code

    def __len__(self):
        return len(self.code)
