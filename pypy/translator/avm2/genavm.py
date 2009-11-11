
import py
from pypy.translator.oosupport.genoo import GenOO
from pypy.translator.avm2.avm2gen import Avm2ilasm
from pypy.translator.avm2.constant import Avm2ConstGenerator, Avm2ClassConst, Avm2InstanceConst, Avm2RecordConst
from pypy.translator.avm2.database import LowLevelDatabase
from pypy.translator.avm2.function import Function
from pypy.translator.avm2.opcodes import opcodes
from pypy.translator.avm2.types_ import Avm2TypeSystem

class GenAVM2(GenOO):
    
    opcodes = opcodes
    Function = Function
    Database = LowLevelDatabase
    TypeSystem = Avm2TypeSystem

    ConstantGenerator = Avm2ConstGenerator

    ClassConst = Avm2ClassConst
    InstanceConst = Avm2InstanceConst
    RecordConst = Avm2RecordConst
    
    def __init__(self, tmpdir, translator, entrypoint, config=None, exctrans=False):
        GenOO.__init__(self, tmpdir, translator, entrypoint, config, exctrans)
        self.const_stat = str(tmpdir.join('const_stat'))
        self.ilasm = None
            
    def create_assembler(self):
        return Avm2ilasm(self)
    
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
