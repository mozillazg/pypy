
import py
from pypy.translator.oosupport.genoo import GenOO
from pypy.translator.avm1.avm1gen import AVM1Gen
from pypy.translator.avm1.constant import AVM1ConstGenerator
from pypy.translator.avm1.database import LowLevelDatabase
from pypy.translator.avm1.function import Function
from pypy.translator.avm1.opcodes import opcodes
from pypy.translator.avm1.types import AVM1TypeSystem

class GenAVM1(GenOO):
    
    opcodes = opcodes
    Function = Function
    Database = LowLevelDatabase
    TypeSystem = AVM1TypeSystem

    ConstantGenerator = AVM1ConstGenerator
    
    def __init__(self, tmpdir, translator, entrypoint, config=None, exctrans=False):
        GenOO.__init__(self, tmpdir, translator, entrypoint, config, exctrans)
        self.const_stat = str(tmpdir.join('const_stat'))
        self.ilasm = None
            
    def create_assembler(self):
        return AVM1Gen()
    
    def generate_source(self):
        if self.ilasm is None:
            self.ilasm = self.create_assembler()
        self.fix_names()
        self.gen_entrypoint()
        self.gen_pendings()
        self.db.gen_constants(self.ilasm)

    # Don't do treebuilding stuff
    def stack_optimization(self):
        pass
