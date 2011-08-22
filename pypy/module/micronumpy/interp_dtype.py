from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.objspace.std.boolobject import W_BoolObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.rlib.rarithmetic import r_int, r_uint, LONG_BIT, LONGLONG_BIT
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.rffi import r_signedchar, r_uchar, r_short, r_ushort, r_long, r_ulong, r_longlong, r_ulonglong

_letters_to_nums = [-1]*256

_letters_to_nums[ord('?')] = 0 # bool
_letters_to_nums[ord('b')] = 1 # int8
_letters_to_nums[ord('B')] = 2 # uint8
_letters_to_nums[ord('h')] = 3 # int16
_letters_to_nums[ord('H')] = 4 # uint16
_letters_to_nums[ord('i')] = 5 # int32
_letters_to_nums[ord('I')] = 6 # uint32
_letters_to_nums[ord('l')] = 7 # long
_letters_to_nums[ord('L')] = 8 # ulong
_letters_to_nums[ord('q')] = 9 # longlong
_letters_to_nums[ord('Q')] = 10 # ulonglong
_letters_to_nums[ord('f')] = 11 # float (float32)
_letters_to_nums[ord('d')] = 12 # double (float64)
_letters_to_nums[ord('g')] = 13 # longdouble (float128)
# need to put in the rest of the type letters

# typenums
Bool_num = 0
Int8_num = 1
UInt8_num = 2
Int16_num = 3
UInt16_num = 4
Int32_num = 5
UInt32_num = 6
Long_num = 7
ULong_num = 8
Int64_num = 9
UInt64_num = 10
Float32_num = 11
Float64_num = 12
Float96_num = 13

# dtype 'kinds'. Used to determine which operations can be performed on array
BOOLLTR = 'b'
FLOATINGLTR = 'f'
SIGNEDLTR = 'i'
UNSIGNEDLTR = 'u'
COMPLEXLTR = 'c'

kind_dict = {'b': 0, 'u': 1, 'i': 1, 'f': 2, 'c': 2}

# this probably doesn't contain all possibilities yet
num_dict = {'b1': Bool_num, 'i1': Int8_num, 'i2': Int16_num, 'i4': Int32_num,
            'i8': Int64_num, 'f4': Float32_num, 'f8': Float64_num, 
            'f12': Float96_num,
            'bool': Bool_num, 'bool8': Bool_num, 'int8': Int8_num,
            'int16': Int16_num, 'int32': Int32_num, 'int64': Int64_num,
            'float32': Float32_num, 'float64': Float64_num,
            'float96': Float96_num}

def unwrap_float(space, val):
    return space.float_w(space.float(val))

def unwrap_int(space, val):
    return space.int_w(space.int(val))

def unwrap_bigint(space, val):
    return space.r_longlong_w(space.long(val))

def unwrap_ubigint(space, val):
    return space.r_ulonglong_w(space.long(val))

def unwrap_bool(space, val):
    return space.is_true(val)

def cast_bool(val):
    return rffi.cast(lltype.Bool, val)

def cast_int8(val):
    return rffi.cast(rffi.SIGNEDCHAR, val)

def cast_uint8(val):
    return rffi.cast(rffi.UCHAR, val)

def cast_int16(val):
    return rffi.cast(rffi.SHORT, val)

def cast_uint16(val):
    return rffi.cast(rffi.USHORT, val)

def cast_int32(val):
    return rffi.cast(rffi.INT, val)

def cast_uint32(val):
    return rffi.cast(rffi.UINT, val)

def cast_long(val):
    return rffi.cast(rffi.LONG, val)

def cast_ulong(val):
    return rffi.cast(rffi.ULONG, val)

def cast_int64(val):
    return rffi.cast(rffi.LONGLONG, val)

def cast_uint64(val):
    return rffi.cast(rffi.ULONGLONG, val)

def cast_float32(val):
    return rffi.cast(lltype.SingleFloat, val)

def cast_float64(val):
    return rffi.cast(lltype.Float, val)

def cast_float96(val):
    return rffi.cast(lltype.LongFloat, val)

def conv_bool(space, val):
    return bool(val)
#    return space.bool(val)

def conv_int(space, val):
    return int(val)
#    return space.int(val)

def conv_float(space, val):
    return float(val)
#    return space.float(val)

class Dtype(Wrappable):
    pass
    # attributes: type, kind, typeobj?(I think it should point to np.float64 or
    # the like), byteorder, flags, type_num, elsize, alignment, subarray,
    # fields, names, f?, metadata. I'll just implement the base minimum for 
    # now. This will include type, kind, typeobj?, byteorder, type_num, elsize,
    # 
#    def descr_num(self, space):
#        return space.wrap(self.num)

    def descr_kind(self, space):
        return space.wrap(self.kind)

    def descr_name(self, space):
        return space.wrap(self.name)

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.name)

    descr_str = descr_name

def make_dtype(_valtype, _TP, _name, convfunc, castfunc, unwrapfunc, _num, _kind):
    class A_Dtype(Dtype):
        #_immutable_fields_ = ["num", "kind", "TP", "conv", "cast", "unwrap"]
        valtype = _valtype
        TP = _TP
        name = _name
        kind = _kind
        num = _num
        def __init__(self):
            self.conv = convfunc
            self.cast = castfunc
            self.unwrap = unwrapfunc

        def getnum(self):
            return _num

        @specialize.argtype(1)
        def convval(self, val):
            return rffi.cast(_TP.OF, val)

    A_Dtype.__name__ = "Dtype_" + _name
    return A_Dtype()

Bool_dtype = make_dtype(True.__class__, lltype.Array(lltype.Bool, hints={'nolength': True}),
    'bool', conv_bool, cast_bool, unwrap_bool, Bool_num, BOOLLTR)
#Int8_dtype = make_dtype(r_signedchar, lltype.Array(rffi.SIGNEDCHAR, hints={'nolength': True}),
#    'int8', conv_int, cast_int8, unwrap_int, Int8_num, SIGNEDLTR)
#UInt8_dtype = make_dtype(r_uchar, lltype.Array(rffi.UCHAR, hints={'nolength': True}),
#    'uint8', conv_int, cast_uint8, unwrap_int, UInt8_num, UNSIGNEDLTR)
#Int16_dtype = make_dtype(r_short, lltype.Array(rffi.SHORT, hints={'nolength': True}),
#    'int16', conv_int, cast_int16, unwrap_int, Int16_num, SIGNEDLTR)
#UInt16_dtype = make_dtype(r_ushort, lltype.Array(rffi.USHORT, hints={'nolength': True}),
#    'uint16', conv_int, cast_uint16, unwrap_int, UInt16_num, UNSIGNEDLTR)
Int32_dtype = make_dtype(r_int, lltype.Array(rffi.INT, hints={'nolength': True}),
    'int32', conv_int, cast_int32, unwrap_int, Int32_num, SIGNEDLTR)
#UInt32_dtype = make_dtype(r_uint, lltype.Array(rffi.UINT, hints={'nolength': True}),
#    'uint32', conv_int, cast_uint32, unwrap_int, UInt32_num, UNSIGNEDLTR)
Long_dtype = make_dtype(r_long, lltype.Array(rffi.LONG, hints={'nolength': True}),
    'int32' if LONG_BIT == 32 else 'int64', 
                    conv_int, cast_long, unwrap_int, Long_num, SIGNEDLTR)
#ULong_dtype = make_dtype(r_ulong, lltype.Array(rffi.ULONG, hints={'nolength': True}),
#    'uint32' if LONG_BIT == 32 else 'uint64',
#                    conv_int, cast_ulong, 
                    #unwrap_ubigint if LONG_BIT == 32 else unwrap_int,
                    #ULong_num, UNSIGNEDLTR)

Int64_dtype = make_dtype(r_longlong, lltype.Array(rffi.LONGLONG, hints={'nolength': True}),
    'int64', conv_int, cast_int64, 
    unwrap_bigint if LONG_BIT == 32 else unwrap_bigint, Int64_num, SIGNEDLTR)
#UInt64_dtype = make_dtype(r_ulonglong, lltype.Array(rffi.ULONGLONG, hints={'nolength': True}),
#    'uint64', conv_int, cast_uint64, unwrap_ubigint, UInt64_num, UNSIGNEDLTR)
#Float32_dtype = make_dtype('float32', conv_float, cast_float32, unwrap_float, Float32_num, FLOATINGLTR)
Float64_dtype = make_dtype(float, lltype.Array(lltype.Float, hints={'nolength': True}),
    'float64', conv_float, cast_float64, unwrap_float, Float64_num, FLOATINGLTR)
#Float96_dtype = make_dtype('float96', conv_float, cast_float96, unwrap_float, Float96_num, FLOATINGLTR)
# This is until we get ShortFloat and LongFloat implemented in the annotator and what not
Float32_dtype = Float64_dtype
Float96_dtype = Float64_dtype
Int8_dtype = Int32_dtype
UInt8_dtype = Int32_dtype
Int16_dtype = Int32_dtype
UInt16_dtype = Int32_dtype
UInt32_dtype = Int32_dtype
ULong_dtype = Int32_dtype
UInt64_dtype = Int32_dtype


_dtype_list = [Bool_dtype,
               Int8_dtype,
               UInt8_dtype,
               Int16_dtype,
               UInt16_dtype,
               Int32_dtype,
               UInt32_dtype,
               Long_dtype,
               ULong_dtype,
               Int64_dtype,
               UInt64_dtype,
               Float32_dtype,
               Float64_dtype,
               Float96_dtype,
]

def find_scalar_dtype(space, scalar):
    if space.is_true(space.isinstance(scalar, space.w_int)):
        return Long_dtype
    if space.is_true(space.isinstance(scalar, space.w_float)):
        return Float64_dtype
    if space.is_true(space.isinstance(scalar, space.w_bool)):
        return Bool_dtype

def find_result_dtype(d1, d2):
    # this function is for determining the result dtype of bin ops, etc.
    # it is kind of a mess so feel free to improve it

    # first make sure larger num is in d2
    if d1.num > d2.num:
        dtype1 = d2
        dtype2 = d1
    else:
        dtype1 = d1
        dtype2 = d2
    num1 = dtype1.num
    num2 = dtype2.num
    kind1 = dtype1.kind
    kind2 = dtype2.kind
    if kind1 == kind2:
        # dtype2 has the greater number
        return dtype2
    kind_num1 = kind_dict[kind1]
    kind_num2 = kind_dict[kind2]
    if kind_num1 == kind_num2: # two kinds of integers or float and complex
        # XXX: Need to deal with float and complex combo here also
        if kind2 == SIGNEDLTR:
            return dtype2
        if num2 < UInt32_num:
            return _dtype_list[num2+1]
        if num2 == UInt64_num or (LONG_BIT == 64 and num2 == Long_num): # UInt64
            return Float64_dtype
        # dtype2 is uint32
        return Int64_dtype
    if kind_num1 == 1: # is an integer
        if num2 == Float32_num and (num1 == UInt64_num or num1 == Int64_num or \
                (LONG_BIT == 64 and (num1 == Long_num or num1 == ULong_num))):
            return Float64_dtype
    return dtype2

def get_dtype(space, str_or_type):
    as_dtype = space.interpclass_w(str_or_type)
    if as_dtype is not None and isinstance(as_dtype, Dtype):
        return as_dtype
    if space.is_true(space.isinstance(str_or_type, space.w_str)):
        s = space.str_w(str_or_type)
        if len(s) == 1:
            typenum = _letters_to_nums[ord(s[0])]
            if typenum != -1:
                dtype = _dtype_list[typenum]
                if dtype is not None:
                    return _dtype_list[typenum]
        # XXX: can improve this part. will need to for endianness
        if s in num_dict:
            return _dtype_list[num_dict[s]]
        raise OperationError(space.w_ValueError,
                            space.wrap("type not recognized"))
    elif space.is_true(space.isinstance(str_or_type, space.w_type)):
        if space.is_w(str_or_type, space.gettypeobject(W_IntObject.typedef)):
            return Long_dtype
        if space.is_w(str_or_type, space.gettypeobject(W_LongObject.typedef)):
            return Int64_dtype
        if space.is_w(str_or_type, space.gettypeobject(W_FloatObject.typedef)):
            return Float64_dtype
        if space.is_w(str_or_type, space.gettypeobject(W_BoolObject.typedef)):
            return Bool_dtype
    raise OperationError(space.w_TypeError,
                            space.wrap("data type not understood"))

def descr_new_dtype(space, w_type, w_string_or_type):
    return space.wrap(get_dtype(space, w_string_or_type))

Dtype.typedef = TypeDef(
    'numpy.dtype',
    __new__  = interp2app(descr_new_dtype),

#    num = GetSetProperty(Dtype.descr_num),
    kind = GetSetProperty(Dtype.descr_kind),
    name = GetSetProperty(Dtype.descr_name),

    __repr__ = interp2app(Dtype.descr_repr),
    __str__ = interp2app(Dtype.descr_str),
)
