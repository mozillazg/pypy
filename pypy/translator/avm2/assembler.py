
from collections import namedtuple
from pypy.translator.avm2.util import Avm2Backpatch, Avm2Label, s24

class BackpatchNotSealed(Error):
    pass

class Avm2CodeAssembler(object):
    
    def __init__(self, constants, initial_local_count=0):
        self.temporaries = [True] * initial_local_count
        self._stack_depth = 0
        self._scope_depth = 0

        self._stack_depth_max = 0
        self._scope_depth_max = 0

        self.code = ""
        self.backpatches = []

        self.flags = 0
        self.constants = constants

    def add_instruction(self, instruction):
        instruction.set_assembler_props(self)
        self.code += instruction.serialize()
        
    def add_instructions(self, *instructions):
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
        if False in self.temporaries:
            return self.temporaries.find(False)
        self.temporaries.append(True)
        return len(self.temporaries) - 1

    def set_local(self, index):
        self.temporaries[index] = True

    def kill_local(self, index):
        self.temporaries[index] = False

    @property
    def local_count(self):
        return len(self.temporaries)
    
    def add_backpatch(self, bkptch):
        self.backpatches.append(bkptch)

    def seal_backpatches(self):
        for b in self.backpatches:
            if backpatch.lbl.address == None:
                raise BackpatchNotSealed("Backpatch never sealed: %s" % backpatch);
            v = backpatch.lbl.address - backpatch.base
            l = backpatch.location
            code[l:l+3] = s24(v)
            
        self.backpatches = []

    def serialize(self):
        self.seal_backpatches()
        return self.code

    def __len__(self):
        return len(self.code)
