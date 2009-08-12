
from pypy.translator.oosupport import constant as c

CONST_OBJNAME = "PYPY_INTERNAL_CONSTANTS"

DEBUG_CONST_INIT = False
DEBUG_CONST_INIT_VERBOSE = False
SERIALIZE = False

# ______________________________________________________________________
# Constant Generators
#
# Different generators implementing different techniques for loading
# constants (Static fields, singleton fields, etc)

class AVM1ConstGenerator(c.BaseConstantGenerator):
    """
    AVM1 constant generator.  It implements the oosupport
    constant generator in terms of the AVM1 virtual machine.
    """

    def __init__(self, db):
        c.BaseConstantGenerator.__init__(self, db)
        self.cts = db.genoo.TypeSystem(db)

    def _begin_gen_constants(self, gen, all_constants):
        gen.push_const(CONST_OBJNAME)
        gen.init_array()
        gen.store_register(CONST_OBJNAME)
        gen.set_variable()
        return gen

    def _end_gen_constants(self, gen, numsteps):
        pass

    def _declare_const(self, gen, const):
        pass
    
    def _close_step(self, gen, stepnum):
        pass
    
    # _________________________________________________________________
    # OOSupport interface
    
    def push_constant(self, gen, const):
        gen.push_var(CONST_OBJNAME)
        gen.push_const(const.name)
        gen.get_member()

    def _create_pointers(self, gen, all_constants):
        pass

    def _initialize_data(self, gen, all_constants):
        """ Iterates through each constant, initializing its data. """
        # gen.add_section("Initialize Data Phase")
        for const in all_constants:
            # gen.add_comment("Constant: %s" % const.name)
            const.initialize_data(self, gen)


class AVM1ArrayListConst(c.ListConst):

    NAME = 'NOT_IMPL'
    
    def __init__(self, db, list, count):
        c.AbstractConst.__init__(self, db, list, count)
        self.name = '%s__%d' % (self.NAME, count)

    def create_pointer(self, gen):
        assert False
        
    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        
        if self._do_not_initialize():
            return

        gen.push_var(CONST_OBJNAME)
        gen.push_const(self.name)
        gen.init_array(self.value._list)
        gen.set_member()
        
        # for idx, item in enumerate(self.value._list):
        #     gen.push_const(CONST_OBJNAME, CONST_OBJNAME)
        #     gen.get_variable()
        #     gen.get_variable()
        #     gen.push_const(self.name, self.name)
        #     gen.get_member()
        #     gen.push_const(idx)
        #     gen.load(item)
        #     gen.set_member()
        #     gen.set_member()

class AVM1ArrayConst(AVM1ArrayListConst):
    NAME = 'ARRAY'

class AVM1ListConst(AVM1ArrayListConst):
    NAME = 'LIST'

class AVM1DictConst(c.DictConst):
    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        
        gen.push_var(CONST_OBJNAME)
        gen.push_const(self.name)
        gen.init_object(self.value._dict)
        gen.set_member()
        
        # for key, value in self.value._dict.iteritems():
        #     gen.push_const(CONST_OBJNAME, CONST_OBJNAME)
        #     gen.get_variable()
        #     gen.get_variable()
        #     gen.push_const(self.name, self.name)
        #     gen.get_member()
        #     gen.load(key)
        #     gen.load(value)
        #     gen.set_member()
        #     gen.set_member()

