#!/usr/bin/env python 
from __future__ import generators
        
from pypy.lang.gameboy.gameboy_implementation import *
from pypy.lang.gameboy.profiling.profiling_cpu import ProfilingCPU
from pypy.lang.gameboy.debug import debug
from pypy.lang.gameboy.debug.debug_socket_memory import *

# GAMEBOY ----------------------------------------------------------------------

class GameBoyProfilingImplementation(GameBoyImplementation):
    
    def __init__(self, cycleLimit=0):
        GameBoyImplementation.__init__(self)
        self.cycleLimit = cycleLimit
        self.cpu = ProfilingCPU(self.interrupt, self)
        self.cpu.cycle_limit = cycleLimit
        
    def handle_executed_op_code(self, is_fetch_execute=True):
        self.process_cpu_profiling_data()
        
    def process_cpu_profiling_data(self):
        self.print_time_used()
        self.print_opcode_histo()
        self.print_fetch_exec_histo()
        
    def print_time_used(self):
        pass
    
    def print_opcode_histo(self):
        pass
    
    def print_fetch_exec_histo(self):
        pass
    
    
# CUSTOM DRIVER IMPLEMENTATIONS currently not used =============================
      
# VIDEO DRIVER -----------------------------------------------------------------

class VideoDriverDebugImplementation(VideoDriverImplementation):
    pass
        
        
# JOYPAD DRIVER ----------------------------------------------------------------

class JoypadDriverDebugImplementation(JoypadDriverImplementation):
    pass
        
        
# SOUND DRIVER -----------------------------------------------------------------

class SoundDriverDebugImplementation(SoundDriverImplementation):
    pass
    
    
# ==============================================================================
