
from __future__ import generators
from pypy.lang.gameboy.cpu import CPU
from pypy.lang.gameboy.debug import debug


class ProfilingCPU(CPU):
    
    
    def __init__(self, interrupt, memory, cycle_limit):
        CPU.__init__(interrupt, memory)
        self.cycle_limit = 0
        self.op_code_count           = 0
        self.fetch_exec_opcode_histo = [0]*(0xFF+1)
        self.opcode_histo            = [0]*(0xFF+1)
    
    def fetch_execute(self):
        CPU.fetch_execute(self)
        self.count += 1
        self.fetch_exec_opcode_histo[self.last_fetch_execute_op_code] += 1
        
    
    def execute(self, opCode):
        CPU.execute(self, opCode)
        self.count += 1
        self.opcode_histo[self.last_op_code] += 1
        if self.op_code_count >= self.cycle_limit:
            raise Exception("Maximal Cyclecount reached")