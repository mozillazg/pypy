from pypy.translator.avm2.metavm import  Call, CallMethod, \
     IndirectCall, GetField, SetField, AddSub, \
     NewArray, OOParseInt, OOParseFloat, \
     TypeOf, GetStaticField, SetStaticField, \
     OOString, ConstCall, ConstCallArgs, PushClass
from pypy.translator.oosupport.metavm import PushArg, PushAllArgs, \
     StoreResult, InstructionList, New, RuntimeNew, CastTo, PushPrimitive, \
     OONewArray, DownCast
from pypy.translator.cli.cts import WEAKREF
from pypy.rpython.ootypesystem import ootype

# some useful instruction patterns
Not = ['not']
DoNothing = [PushAllArgs]
DontStoreResult = object()
Ignore = []

def _not(op):
    return [PushAllArgs, op, 'not']

# def _check_ovf(op):
#     mapping = [('[mscorlib]System.OverflowException', 'exceptions.OverflowError')]
#     return [MapException(op, mapping)]

# def _check_zer(op):
#     mapping = [('[mscorlib]System.DivideByZeroException', 'exceptions.ZeroDivisionError')]
#     return [MapException(op, mapping)]

# __________ object oriented & misc operations __________
misc_ops = {
    'new':                      [New],
    'runtimenew':               [RuntimeNew],
    'oosetfield':               [SetField],
    'oogetfield':               [GetField],
    'oosend':                   [CallMethod],
    'ooupcast':                 DoNothing,
    'oodowncast':               [DownCast],
#    'clibox':                   [Box],
#    'cliunbox':                 [Unbox],
    # 'cli_newarray':             [NewArray],
    # 'cli_getelem':              [GetArrayElem],
    # 'cli_setelem':              [SetArrayElem],
    # 'cli_typeof':               [TypeOf],
    # 'cli_arraylength':          'ldlen',
    # 'cli_eventhandler':         [EventHandler],
    # 'cli_getstaticfield':       [GetStaticField],
    # 'cli_setstaticfield':       [SetStaticField],
    # 'cli_fieldinfo_for_const':  [FieldInfoForConst],
    'oois':                     'strictequals',
#    'oononnull':                [PushAllArgs, 'pushnull', 'equals', 'not'],
    'oononnull':                [PushAllArgs, 'convert_b'],
    'ooisnull':                 [PushAllArgs, 'pushnull', 'equals'],
    'classof':                  [PushAllArgs, TypeOf],
    'instanceof':               [CastTo],
    'subclassof':               [CastTo],
    'ooidentityhash':           [PushAllArgs, 'callvirt instance int32 object::GetHashCode()'],
    'oohash':                   [PushAllArgs, 'callvirt instance int32 object::GetHashCode()'],    
    'oostring':                 [OOString],
    'oounicode':                [OOString],
    'ooparse_int':              [PushAllArgs, OOParseInt],
    'ooparse_float':            [PushAllArgs, OOParseFloat],
#    'oonewcustomdict':          [NewCustomDict],
    'oonewarray':               [OONewArray],
    
    'hint':                     [PushArg(0)],
    'direct_call':              [Call],
    'indirect_call':            [IndirectCall],

    'cast_ptr_to_weakadr':      [PushAllArgs, 'newobj instance void class %s::.ctor(object)' % WEAKREF],
    'gc__collect':              'call void class [mscorlib]System.GC::Collect()',
    'gc_set_max_heap_size':     Ignore,
    'resume_point':             Ignore,
    'debug_assert':             Ignore,
    'keepalive':                Ignore,
    'is_early_constant':        [PushPrimitive(ootype.Bool, False)],
    }

# __________ numeric operations __________

unary_ops = {
    'same_as':                  DoNothing,
    
    'bool_not':                 [PushAllArgs]+Not,

    'int_is_true':              [PushAllArgs, PushPrimitive(ootype.Signed, 0), 'equals', 'not'],
    'int_neg':                  'negate_i',
#    'int_neg_ovf':              _check_ovf(['ldc.i4.0', PushAllArgs, 'sub.ovf', StoreResult]),
#    'int_abs':                  _abs('int32'),
#    'int_abs_ovf':              _check_ovf(_abs('int32')),
    'int_invert':               'not',

    'uint_is_true':             [PushAllArgs, PushPrimitive(ootype.Unsigned, 0), 'greaterthan'],
    'uint_invert':              'not',

    'float_is_true':            [PushAllArgs, PushPrimitive(ootype.Float, 0), 'equals', 'not'],
    'float_neg':                'negate',
#    'float_abs':                _abs('float64'),

    'llong_is_true':            [PushAllArgs, PushPrimitive(ootype.Signed, 0), 'equals', 'not'],
    'llong_neg':                'negate_i',
#    'llong_neg_ovf':            _check_ovf(['ldc.i8 0', PushAllArgs, 'sub.ovf', StoreResult]),
#    'llong_abs':                _abs('int64'),
#    'llong_abs_ovf':            _check_ovf(_abs('int64')),
    'llong_invert':             'not',

    'ullong_is_true':            [PushAllArgs, PushPrimitive(ootype.Unsigned, 0), 'greaterthan'],
    'ullong_invert':             'not',

    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick.
    'cast_bool_to_int':         'convert_i',
    'cast_bool_to_uint':        'convert_u',
    'cast_bool_to_float':       'convert_d',
    'cast_char_to_int':         [PushAllArgs, ConstCall("charCodeAt", 0)],
    'cast_unichar_to_int':      [PushAllArgs, ConstCall("charCodeAt", 0)],
    'cast_int_to_char':         [PushAllArgs, PushClass("String"), ConstCallArgs("fromCharCode", 1)],
    'cast_int_to_unichar':      [PushAllArgs, PushClass("String"), ConstCallArgs("fromCharCode", 1)],
    'cast_int_to_uint':         'convert_i',
    'cast_int_to_float':        'convert_d',
    'cast_int_to_longlong':     DoNothing,
    'cast_uint_to_int':         DoNothing,
    'cast_uint_to_float':       'convert_d',
    'cast_float_to_int':        'convert_i',
    'cast_float_to_uint':       'convert_u',
    'cast_longlong_to_float':   'convert_d',
    'cast_float_to_longlong':   'convert_i',
#    'cast_primitive':           [PushAllArgs, CastPrimitive],
    'truncate_longlong_to_int': 'convert_i',
    }

binary_ops = {
    'char_lt':                  'lessthan',
    'char_le':                  'lessequals',
    'char_eq':                  'equals',
    'char_ne':                  _not('equals'),
    'char_gt':                  'greaterthan',
    'char_ge':                  'greaterequals',

    'unichar_eq':               'equals',
    'unichar_ne':               _not('equals'),

    'int_add':                  'add_i',
    'int_add_ovf':              'add_i',
    'int_add_nonneg_ovf':       'add_i',
    'int_sub':                  'subtract_i',
    'int_sub_ovf':              'subtract_i',
    'int_mul':                  'multiply_i',
    'int_mul_ovf':              'multiply_i',
    'int_floordiv':             [PushAllArgs, 'divide', 'convert_i'],
#    'int_floordiv_zer':         _check_zer('div'),
    'int_mod':                  'modulo',
    'int_lt':                   'lessthan',
    'int_le':                   'lessequals',
    'int_eq':                   'equals',
    'int_ne':                   _not('equals'),
    'int_gt':                   'greaterthan',
    'int_ge':                   'greaterequals',
    'int_and':                  'bitand',
    'int_or':                   'bitor',
    'int_lshift':               'lshift',
    'int_rshift':               'rshift',
    'int_xor':                  'bitxor',
#    'int_add_ovf':              _check_ovf('add.ovf'),

#    'int_sub_ovf':              _check_ovf('sub.ovf'),
#    'int_mul_ovf':              _check_ovf('mul.ovf'),
    'int_floordiv_ovf':         'divide', # these can't overflow!
    'int_mod_ovf':              'modulo',
    'int_lt_ovf':               'lessthan',
    'int_le_ovf':               'lessequals',
    'int_eq_ovf':               'equals',
    'int_ne_ovf':               _not('equals'),
    'int_gt_ovf':               'greaterthan',
    'int_ge_ovf':               'greaterequals',
    'int_and_ovf':              'bitand',
    'int_or_ovf':               'bitor',

#    'int_lshift_ovf':           _check_ovf([PushArg(0),'conv.i8',PushArg(1), 'shl',
#                                            'conv.ovf.i4', StoreResult]),
#    'int_lshift_ovf_val':       _check_ovf([PushArg(0),'conv.i8',PushArg(1), 'shl',
#                                            'conv.ovf.i4', StoreResult]),

    'int_rshift_ovf':           'rshift', # these can't overflow!
    'int_xor_ovf':              'bitxor',
#    'int_floordiv_ovf_zer':     _check_zer('div'),
#    'int_mod_ovf_zer':          _check_zer('rem'),
#    'int_mod_zer':              _check_zer('rem'),

    'uint_add':                 'add_i',
    'uint_sub':                 'subtract_i',
    'uint_mul':                 'multiply_i',
    'uint_div':                 'divide',
    'uint_floordiv':            [PushAllArgs, 'divide', 'convert_u'],
    'uint_mod':                 'modulo',
    'uint_lt':                  'lessthan',
    'uint_le':                  'lessequals',
    'uint_eq':                  'equals',
    'uint_ne':                  _not('equals'),
    'uint_gt':                  'greaterthan',
    'uint_ge':                  'greaterequals',
    'uint_and':                 'bitand',
    'uint_or':                  'bitor',
    'uint_lshift':              'lshift',
    'uint_rshift':              'urshift',
    'uint_xor':                 'bitxor',

    'float_add':                'add',
    'float_sub':                'subtract',
    'float_mul':                'multiply',
    'float_truediv':            'divide', 
    'float_lt':                 'lessthan',
    'float_le':                 'lessequals',
    'float_eq':                 'equals',
    'float_ne':                 _not('equals'),
    'float_gt':                 'greaterthan',
    'float_ge':                 'greaterequals',

    'llong_add':                'add_i',
    'llong_sub':                'subtract_i',
    'llong_mul':                'multiply_i',
    'llong_div':                'divide',
    'llong_floordiv':           [PushAllArgs, 'divide', 'convert_i'],
#    'llong_floordiv_zer':       _check_zer('div'),
    'llong_mod':                'modulo',
#    'llong_mod_zer':            _check_zer('rem'),
    'llong_lt':                 'lessthan',
    'llong_le':                 'lessequals',
    'llong_eq':                 'equals',
    'llong_ne':                 _not('equals'),
    'llong_gt':                 'greaterthan',
    'llong_ge':                 'lessthan',
    'llong_and':                'bitand',
    'llong_or':                 'bitor',
    'llong_lshift':             'lshift',
    'llong_rshift':             'rshift',
    'llong_xor':                'bitxor',

    'ullong_add':               'add_i',
    'ullong_sub':               'subtract_i',
    'ullong_mul':               'multiply_i',
    'ullong_div':               'divide',
    'ullong_floordiv':          [PushAllArgs, 'divide', 'convert_u'],
    'ullong_mod':               'modulo',
    'ullong_lt':                'lessthan',
    'ullong_le':                'lessequals',
    'ullong_eq':                'equals',
    'ullong_ne':                _not('equals'),
    'ullong_gt':                'greaterthan',
    'ullong_ge':                'greaterequals',
    'ullong_lshift':            'lshift',
    'ullong_rshift':            'urshift',
}

opcodes = misc_ops.copy()
opcodes.update(unary_ops)
opcodes.update(binary_ops)

for key, value in opcodes.iteritems():
    if type(value) is str:
        value = InstructionList([PushAllArgs, value, StoreResult])
    elif value is not None:
        if DontStoreResult in value:
            value.remove(DontStoreResult)
        elif value is not Ignore and StoreResult not in value:
            value.append(StoreResult)
        value = InstructionList(value)

    opcodes[key] = value

