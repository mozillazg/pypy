
from pypy.translator.oosupport.constant import BaseConstantGenerator

CONST_OBJNAME = "PYPY_INTERNAL_CONSTANTS"

DEBUG_CONST_INIT = False
DEBUG_CONST_INIT_VERBOSE = False
SERIALIZE = False

# ______________________________________________________________________
# Constant Generators
#
# Different generators implementing different techniques for loading
# constants (Static fields, singleton fields, etc)

class AVM1ConstGenerator(BaseConstantGenerator):
    """
    AVM1 constant generator.  It implements the oosupport
    constant generator in terms of the AVM1 virtual machine.
    """

    def __init__(self, db):
        BaseConstantGenerator.__init__(self, db)
        self.cts = db.genoo.TypeSystem(db)

    def _begin_gen_constants(self, asmgen, all_constants):
        self.asmgen = asmgen
        self.asmgen.init_object()
        self.asmgen.store_register(CONST_OBJNAME)
        self.asmgen.push_const(CONST_OBJNAME)
        self.asmgen.set_variable()
        return asmgen
    
    # _________________________________________________________________
    # OOSupport interface
    
    def push_constant(self, gen, const):
        gen.asmgen.push_var(CONST_OBJNAME)
        gen.asmgen.push_const(const.name)
        gen.asmgen.get_member()

    def _store_constant(self, gen, const):
        gen.asmgen.set_static_field(CONST_OBJNAME, const.name)
