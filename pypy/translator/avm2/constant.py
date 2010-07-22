
from pypy.translator.oosupport.constant import \
     push_constant, WeakRefConst, StaticMethodConst, CustomDictConst, \
     ListConst, ClassConst, InstanceConst, RecordConst, DictConst, \
     BaseConstantGenerator, AbstractConst, ArrayConst
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2 import types_ as types
from pypy.rpython.lltypesystem import lltype

from mech.fusion.avm2.traits import AbcConstTrait
from mech.fusion.avm2.constants import QName, packagedQName
from mech.fusion.avm2.interfaces import IMultiname

from zope.interface import implementer
from zope.component import adapter, provideAdapter

CONST_CLASS = packagedQName("pypy.runtime", "Constants")

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
        self.ctx.add_static_trait(AbcConstTrait(IMultiname(const.name), IMultiname(const)))

    def downcast_constant(self, gen, const, EXPECTED_TYPE):
        type = self.cts.lltype_to_cts(EXPECTED_TYPE)
        gen.emit('coerce', IMultiname(type))
 
    def _get_key_for_const(self, value):
        if isinstance(value, ootype._view) and isinstance(value._inst, ootype._record):
            return value._inst
        return BaseConstantGenerator._get_key_for_const(self, value)
    
    def push_constant(self, gen, const):
        gen.emit('getlex', CONST_CLASS)
        gen.emit('getproperty', IMultiname(const.name))

    def _push_constant_during_init(self, gen, const):
        gen.push_this()
        gen.emit('getproperty', IMultiname(const.name))

    def _pre_store_constant(self, gen, const):
        gen.push_this()
    
    def _store_constant(self, gen, const):
        gen.emit('initproperty', IMultiname(const.name))

    def _initialize_data(self, gen, all_constants):
        """ Iterates through each constant, initializing its data. """
        for const in all_constants:
            if const._do_not_initialize():
                continue
            self._push_constant_during_init(gen, const)
            self.current_const = const
            if not const.initialize_data(self, gen):
                gen.pop()

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
# Mixins are used to add a few Tamarin-specific methods to each constant
# class.  Basically, any time I wanted to extend a base class (such as
# AbstractConst or DictConst), I created a mixin, and then mixed it in
# to each sub-class of that base-class.  Kind of awkward.

class Avm2BaseConstMixin(object):
    """ A mix-in with a few extra methods the Tamarin backend uses """
    
    def get_type(self):
        """ Returns the Tamrin type for this constant's representation """
        return self.cts.lltype_to_cts(self.value._TYPE)
    
    def push_inline(self, gen, TYPE):
        """ Overload the oosupport version so that we use the Tamarin
        opcode for pushing NULL """
        assert self.is_null()
        gen.ilasm.push_null()

@adapter(Avm2BaseConstMixin)
@implementer(IMultiname)
def _adapter(self):
    return IMultiname(self.get_type())

provideAdapter(_adapter)

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
# the generator interface in Tamarin.

class Avm2RecordConst(Avm2BaseConstMixin, RecordConst):
    def _do_not_initialize(self):
        return False

    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        SELFTYPE = self.value._TYPE
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            if FIELD_TYPE is not ootype.Void:
                gen.dup()
                value = self.value._items[f_name]
                push_constant(self.db, FIELD_TYPE, value, gen)
                gen.set_field(f_name)

class Avm2InstanceConst(Avm2BaseConstMixin, InstanceConst):
    def _do_not_initialize(self):
        return not self.value._TYPE._fields

    def initialize_data(self, constgen, gen):
        assert not self.is_null()

        # Get a list of all the constants we'll need to initialize.
        # I am not clear on why this needs to be sorted, actually,
        # but we sort it.
        const_list = self._sorted_const_list()
        
        # Push ourself on the stack, and cast to our actual type if it
        # is not the same as our static type
        SELFTYPE = self.value._TYPE
        if SELFTYPE is not self.static_type:
            gen.downcast(SELFTYPE)

        # Store each of our fields in the sorted order
        for FIELD_TYPE, INSTANCE, name, value in const_list:
            constgen._consider_split_current_function(gen)
            gen.dup()
            push_constant(self.db, FIELD_TYPE, value, gen)
            gen.set_field(name)

class Avm2ClassConst(Avm2BaseConstMixin, ClassConst):
    def is_inline(self):
        return True

    def _do_not_initialize(self):
        return True

    def push_inline(self, gen, EXPECTED_TYPE):
        if not self.is_null():
            INSTANCE = self.value._INSTANCE
            classname = self.cts.instance_to_qname(INSTANCE)
            return gen.load(classname)

class Avm2ArrayListConst(Avm2BaseConstMixin):
    def get_value(self):
        pass

    def get_length(self):
        return len(self.get_value())

    def _do_not_initialize(self):
        # Check if it is a list of all zeroes:
        try:
            return self.get_value() == [0] * self.get_length()
        except:
            return False

    def create_pointer(self, gen):
        gen.oonewarray(self.value._TYPE, self.get_length())

    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        ITEM = self.value._TYPE.ITEM

        # check for special cases and avoid initialization
        if self._do_not_initialize():
            return

        for idx, item in enumerate(self.get_value()):
            gen.dup()
            push_constant(self.db, ITEM, item, gen)
            gen.set_field(idx)

class Avm2ListConst (Avm2ArrayListConst, ListConst):
    def get_value(self):
        return self.value._list

class Avm2ArrayConst(Avm2ArrayListConst, ArrayConst):
    def get_value(self):
        return self.value._array

# class CLIDictConst(CLIDictMixin, DictConst):
#     def create_pointer(self, gen):
#         self.db.const_count.inc('Dict')
#         self.db.const_count.inc('Dict', self.value._TYPE._KEYTYPE, self.value._TYPE._VALUETYPE)
#         super(CLIDictConst, self).create_pointer(gen)        
