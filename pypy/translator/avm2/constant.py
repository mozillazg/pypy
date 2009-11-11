"""
___________________________________________________________________________
CLI Constants

This module extends the oosupport/constant.py to be specific to the
CLI.  Most of the code in this file is in the constant generators, which
determine how constants are stored and loaded (static fields, lazy
initialization, etc), but some constant classes have been overloaded or
extended to allow for special handling.

The CLI implementation is broken into three sections:

* Constant Generators: different generators implementing different
  techniques for loading constants (Static fields, singleton fields, etc)

* Mixins: mixins are used to add a few CLI-specific methods to each
  constant class.  Basically, any time I wanted to extend a base class
  (such as AbstractConst or DictConst), I created a mixin, and then
  mixed it in to each sub-class of that base-class.

* Subclasses: here are the CLI specific classes.  Eventually, these
  probably wouldn't need to exist at all (the JVM doesn't have any,
  for example), or could simply have empty bodies and exist to
  combine a mixin and the generic base class.  For now, though, they
  contain the create_pointer() and initialize_data() routines.
"""

from pypy.translator.oosupport.constant import \
     push_constant, WeakRefConst, StaticMethodConst, CustomDictConst, \
     ListConst, ClassConst, InstanceConst, RecordConst, DictConst, \
     BaseConstantGenerator, AbstractConst, ArrayConst
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.comparer import EqualityComparer
from pypy.translator.avm2 import constants, types_ as types, traits
from pypy.rpython.lltypesystem import lltype

CONST_CLASS = constants.packagedQName("pypy.runtime", "Constants")

DEBUG_CONST_INIT = False
DEBUG_CONST_INIT_VERBOSE = False
SERIALIZE = False

# ______________________________________________________________________
# Constant Generators
#
# Different generators implementing different techniques for loading
# constants (Static fields, singleton fields, etc)

class Avm2ConstGenerator(BaseConstantGenerator):

    def __init__(self, db):
        BaseConstantGenerator.__init__(self, db)
        self.cts = db.genoo.TypeSystem(db)

    def _begin_gen_constants(self, gen, all_constants):
        self.ilasm = gen
        self.begin_class()
        return gen

    def _end_gen_constants(self, gen, numsteps):
        assert gen is self.ilasm
        self.end_class()

    def begin_class(self):
        self.ctx = self.ilasm.begin_class(CONST_CLASS)
        self.ctx.make_cinit()

    def end_class(self):
        self.ilasm.exit_context()
        self.ilasm.exit_context()
    
    def _declare_const(self, gen, const):
        self.ctx.add_static_trait(traits.AbcConstTrait(constants.QName(const.name), const.get_type().multiname()))

    def downcast_constant(self, gen, const, EXPECTED_TYPE):
        type = self.cts.lltype_to_cts(EXPECTED_TYPE)
        gen.emit('coerce', type.multiname())
 
    def _get_key_for_const(self, value):
        if isinstance(value, ootype._view) and isinstance(value._inst, ootype._record):
            return value._inst
        return BaseConstantGenerator._get_key_for_const(self, value)
    
    def push_constant(self, gen, const):
        type_ = const.get_type()
        gen.emit('getlex', CONST_CLASS)
        gen.emit('getproperty', constants.QName(const.name))

    #def _push_constant_during_init(self, gen, const):
    #    self.push_constant(gen, const)
    #    gen.store_var('current_constant')

    def _store_constant(self, gen, const):
        type_ = const.get_type()
        gen.emit('getlex', CONST_CLASS)
        gen.emit('setproperty', constants.QName(const.name))

    def _declare_step(self, gen, stepnum):
        pass

    def _close_step(self, gen, stepnum):
        pass

    # def _create_complex_const(self, value):
        # if isinstance(value, _fieldinfo):
        #     uniq = self.db.unique()
        #     return CLIFieldInfoConst(self.db, value.llvalue, uniq)
        # elif isinstance(value, ootype._view) and isinstance(value._inst, ootype._record):
        #     self.db.cts.lltype_to_cts(value._inst._TYPE) # record the type of the record
        #     return self.record_const(value._inst)
        # else:
        #     return BaseConstantGenerator._create_complex_const(self, value)


# ______________________________________________________________________
# Mixins
#
# Mixins are used to add a few CLI-specific methods to each constant
# class.  Basically, any time I wanted to extend a base class (such as
# AbstractConst or DictConst), I created a mixin, and then mixed it in
# to each sub-class of that base-class.  Kind of awkward.

class Avm2BaseConstMixin(object):
    """ A mix-in with a few extra methods the CLI backend uses """
    
    def get_type(self):
        """ Returns the CLI type for this constant's representation """
        return self.cts.lltype_to_cts(self.value._TYPE)
    
    def push_inline(self, gen, TYPE):
        """ Overload the oosupport version so that we use the CLI opcode
        for pushing NULL """
        assert self.is_null()
        gen.ilasm.opcode('pushnull')

# class Avm2DictMixin(Avm2BaseConstMixin):
#     def _check_for_void_dict(self, gen):
#         KEYTYPE = self.value._TYPE._KEYTYPE
#         keytype = self.cts.lltype_to_cts(KEYTYPE)
#         keytype_T = self.cts.lltype_to_cts(self.value._TYPE.KEYTYPE_T)
#         VALUETYPE = self.value._TYPE._VALUETYPE
#         valuetype = self.cts.lltype_to_cts(VALUETYPE)
#         valuetype_T = self.cts.lltype_to_cts(self.value._TYPE.VALUETYPE_T)
#         if VALUETYPE is ootype.Void:
#             gen.add_comment('  CLI Dictionary w/ void value')
#             class_name = PYPY_DICT_OF_VOID % keytype
#             for key in self.value._dict:
#                 gen.ilasm.opcode('dup')
#                 push_constant(self.db, KEYTYPE, key, gen)
#                 meth = 'void class %s::ll_set(%s)' % (class_name, keytype_T)
#                 gen.ilasm.call_method(meth, False)
#             return True
#         return False
    
#     def initialize_data(self, constgen, gen):
#         # special case: dict of void, ignore the values
#         if self._check_for_void_dict(gen):
#             return 
#         return super(Avm2DictMixin, self).initialize_data(constgen, gen)

# ______________________________________________________________________
# Constant Classes
#
# Here we overload a few methods, and mix in the base classes above.
# Note that the mix-ins go first so that they overload methods where
# required.
#
# Eventually, these probably wouldn't need to exist at all (the JVM
# doesn't have any, for example), or could simply have empty bodies
# and exist to combine a mixin and the generic base class.  For now,
# though, they contain the create_pointer() and initialize_data()
# routines.  In order to get rid of them, we would need to implement
# the generator interface in the CLI.

class Avm2RecordConst(Avm2BaseConstMixin, RecordConst):
    def create_pointer(self, gen):
        self.db.const_count.inc('Record')
        super(Avm2RecordConst, self).create_pointer(gen)

class Avm2InstanceConst(Avm2BaseConstMixin, InstanceConst):
    def create_pointer(self, gen):
        self.db.const_count.inc('Instance')
        self.db.const_count.inc('Instance', self.OOTYPE())
        super(Avm2InstanceConst, self).create_pointer(gen)


class Avm2ClassConst(Avm2BaseConstMixin, ClassConst):
    def is_inline(self):
        return True

    def push_inline(self, gen, EXPECTED_TYPE):
        if not self.is_null():
            if hasattr(self.value, '_FUNC'):
                FUNC = self.value._FUNC
                classname = self.db.record_delegate(FUNC)
            else:
                INSTANCE = self.value._INSTANCE
                classname = self.db.class_name(INSTANCE)
            gen.emit('getlex', constants.QName(classname))
            return
        super(Avm2ClassConst, self).push_inline(gen, EXPECTED_TYPE)

# class CLIListConst(CLIBaseConstMixin, ListConst):

#     def _do_not_initialize(self):
#         # Check if it is a list of all zeroes:
#         try:
#             if self.value._list == [0] * len(self.value._list):
#                 return True
#         except:
#             pass
#         return super(CLIListConst, self)._do_not_initialize()
    
#     def create_pointer(self, gen):
#         self.db.const_count.inc('List')
#         self.db.const_count.inc('List', self.value._TYPE.ITEM)
#         self.db.const_count.inc('List', len(self.value._list))
#         super(CLIListConst, self).create_pointer(gen)


# class CLIArrayConst(CLIBaseConstMixin, ArrayConst):

#     def _do_not_initialize(self):
#         # Check if it is an array of all zeroes:
#         try:
#             if self.value._list == [0] * len(self.value._list):
#                 return True
#         except:
#             pass
#         return super(CLIArrayConst, self)._do_not_initialize()

#     def _setitem(self, SELFTYPE, gen):
#         gen.array_setitem(SELFTYPE)


# class CLIDictConst(CLIDictMixin, DictConst):
#     def create_pointer(self, gen):
#         self.db.const_count.inc('Dict')
#         self.db.const_count.inc('Dict', self.value._TYPE._KEYTYPE, self.value._TYPE._VALUETYPE)
#         super(CLIDictConst, self).create_pointer(gen)        
