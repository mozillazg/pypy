
from pypy.translator.oosupport import metavm as om
from pypy.translator.avm import metavm as am, avm1 as a

DoNothing = [om.PushAllArgs]

misc_ops = {
    'new':           [om.New],
    'runtimenew':    [om.RuntimeNew],
    'oosetfield':    [am.SetField],
    'oogetfield':    [am.GetField],
#    'oosend':        am.CallMethod
}

unary_ops = {
    'same_as':                DoNothing,
    'bool_not':               'not',
    'int_neg':                'negate',
    'int_neg_ovf':            'negate',
    'int_abs':                [am.PushArgsForFunctionCall, am.CallConstantMethod("Math", "abs")],

    'cast_int_to_char':       [am.PushArgsForFunctionCall, am.CallConstantMethod("String", "fromCharCode")],
    'cast_int_to_unichar':    [am.PushArgsForFunctionCall, am.CallConstantMethod("String", "fromCharCode")],
    'cast_int_to_float':      DoNothing,
    'cast_int_to_longlong':   DoNothing,
    'cast_int_to_uint':       DoNothing,
    'cast_int_to_long':       DoNothing,
    'cast_uint_to_float':     DoNothing,
    'cast_uint_to_longlong':  DoNothing,
    'cast_uint_to_int' :      DoNothing,
    'cast_uint_to_long':      DoNothing,

    'cast_bool_to_int':       'convert_to_number',
    'cast_bool_to_uint':      'convert_to_number',
    'cast_bool_to_float':     'convert_to_number',

   
}

binary_ops = {
    'int_add':              'typed_add',
    'int_sub':              'subtract',
    'int_mul':              'multiply',
    'int_floordiv':         [om.PushAllArgs, 'divide', am.PushConst(1), am.CallConstantMethod("Math", "floor")],
    'int_mod':              'modulo',
    'int_lt':               'typed_less',
    'int_le':               [om.PushAllArgs, 'greater', 'not'],
    'int_eq':               'typed_equals',
    'int_ne':               [om.PushAllArgs, 'typed_equals', 'not'],
    'int_gt':               'greater',
    'int_ge':               [om.PushAllArgs, 'typed_less', 'not'],

    'int_and':              'bit_and',
    'int_or':               'bit_or',
    'int_lshift':           'shift_left',
    'int_rshift':           'shift_right',
    'int_xor':              'bit_xor',

    'uint_add':              'typed_add',
    'uint_sub':              'subtract',
    'uint_mul':              'multiply',
    'uint_floordiv':         [om.PushAllArgs, 'divide', am.PushConst(1), am.CallConstantMethod("Math", "floor")],
    'uint_mod':              'modulo',
    'uint_lt':               'typed_less',
    'uint_le':               [om.PushAllArgs, 'greater', 'not'],
    'uint_eq':               'typed_equals',
    'uint_ne':               [om.PushAllArgs, 'typed_equals', 'not'],
    'uint_gt':               'greater',
    'uint_ge':               [om.PushAllArgs, 'typed_less', 'not'],

    'uint_and':              'bit_and',
    'uint_or':               'bit_or',
    'uint_lshift':           'shift_left',
    'uint_rshift':           'shift_right',
    'uint_xor':              'bit_xor',
    
    'float_add':              'typed_add',
    'float_sub':              'subtract',
    'float_mul':              'multiply',
    'float_floordiv':         [om.PushAllArgs, 'divide', am.PushConst(1), am.CallConstantMethod("Math", "floor")],
    'float_mod':              'modulo',
    'float_lt':               'typed_less',
    'float_le':               [om.PushAllArgs, 'greater', 'not'],
    'float_eq':               'typed_equals',
    'float_ne':               [om.PushAllArgs, 'typed_equals', 'not'],
    'float_gt':               'greater',
    'float_ge':               [om.PushAllArgs, 'typed_less', 'not'],

    'float_and':              'bit_and',
    'float_or':               'bit_or',
    'float_lshift':           'shift_left',
    'float_rshift':           'shift_right',
    'float_xor':              'bit_xor',
    
    'llong_add':              'typed_add',
    'llong_sub':              'subtract',
    'llong_mul':              'multiply',
    'llong_floordiv':         [om.PushAllArgs, 'divide', am.PushConst(1), am.CallConstantMethod("Math", "floor")],
    'llong_mod':              'modulo',
    'llong_lt':               'typed_less',
    'llong_le':               [om.PushAllArgs, 'greater', 'not'],
    'llong_eq':               'typed_equals',
    'llong_ne':               [om.PushAllArgs, 'typed_equals', 'not'],
    'llong_gt':               'greater',
    'llong_ge':               [om.PushAllArgs, 'typed_less', 'not'],

    'llong_and':              'bit_and',
    'llong_or':               'bit_or',
    'llong_lshift':           'shift_left',
    'llong_rshift':           'shift_right',
    'llong_xor':              'bit_xor',

    'ullong_add':              'typed_add',
    'ullong_sub':              'subtract',
    'ullong_mul':              'multiply',
    'ullong_floordiv':         [om.PushAllArgs, 'divide', am.PushConst(1), am.CallConstantMethod("Math", "floor")],
    'ullong_mod':              'modulo',
    'ullong_lt':               'typed_less',
    'ullong_le':               [om.PushAllArgs, 'greater', 'not'],
    'ullong_eq':               'typed_equals',
    'ullong_ne':               [om.PushAllArgs, 'typed_equals', 'not'],
    'ullong_gt':               'greater',
    'ullong_ge':               [om.PushAllArgs, 'typed_less', 'not'],
    'ullong_lshift':           'shift_left',
    'ullong_rshift':           'shift_right',
}

opcodes = misc_ops.copy()
opcodes.update(unary_ops)
opcodes.update(binary_ops)

for key, value in opcodes.iteritems():
    if isinstance(value, str):
        value = [am.StoreResultStart, om.PushAllArgs, value, am.StoreResultEnd]
    if am.StoreResultStart not in value:
        value.insert(0, am.StoreResultStart)
    if am.StoreResultEnd not in value:
        value.append(am.StoreResultEnd)
    value = om.InstructionList(value)
    opcodes[key] = value
