
import py
from pypy.translator.oosupport.genoo import GenOO
from pypy.translator.avm2.avm1gen import Avm2ilasm
from pypy.translator.avm2.constant import AVM1ConstGenerator
from pypy.translator.avm2.database import LowLevelDatabase
from pypy.translator.avm2.function import Function
from pypy.translator.avm2.opcodes import opcodes
from pypy.translator.avm2.types import AVM1TypeSystem

class GenAVM2(GenOO):
    
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
