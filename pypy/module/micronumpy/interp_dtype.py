from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rlib.rarithmetic import r_int, r_uint, LONG_BIT, LONGLONG_BIT
from pypy.rpython.lltypesystem import lltype, rffi

_letters_to_nums = [-1]*128

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

class Dtype(Wrappable):
    # attributes: type, kind, typeobj?(I think it should point to np.float64 or
    # the like), byteorder, flags, type_num, elsize, alignment, subarray,
    # fields, names, f?, metadata. I'll just implement the base minimum for 
    # now. This will include type, kind, typeobj?, byteorder, type_num, elsize,
    # 
    def __init__(self, castfunc, unwrapfunc, num, kind):
        # doesn't handle align and copy parameters yet
        # only deals with simple strings e.g., 'uint32', and type objects
        self.cast = castfunc
        self.unwrap = unwrapfunc
        self.num = num
        self.kind = kind

    def descr_num(self, space):
        return space.wrap(self.num)

    def descr_kind(self, space):
        return space.wrap(self.kind)

def unwrap_float(space, val):
    return space.float_w(space.float(val))

def unwrap_int(space, val):
    return space.int_w(space.int(val))

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

Bool_dtype = Dtype(cast_bool, unwrap_bool, Bool_num, BOOLLTR)
Int8_dtype = Dtype(cast_int8, unwrap_int, Int8_num, SIGNEDLTR)
UInt8_dtype = Dtype(cast_uint8, unwrap_int, UInt8_num, SIGNEDLTR)
Int16_dtype = Dtype(cast_int16, unwrap_int, Int16_num, SIGNEDLTR)
UInt16_dtype = Dtype(cast_uint16, unwrap_int, UInt16_num, SIGNEDLTR)
Int32_dtype = Dtype(cast_int32, unwrap_int, Int32_num, SIGNEDLTR)
UInt32_dtype = Dtype(cast_uint32, unwrap_int, UInt32_num, UNSIGNEDLTR)
Long_dtype = Dtype(cast_long, unwrap_int, Long_num, SIGNEDLTR)
ULong_dtype = Dtype(cast_ulong, unwrap_int, ULong_num, UNSIGNEDLTR)
Int64_dtype = Dtype(cast_int64, unwrap_int, Int64_num, SIGNEDLTR)
UInt64_dtype = Dtype(cast_uint64, unwrap_int, UInt64_num, UNSIGNEDLTR)
Float32_dtype = Dtype(cast_float32, unwrap_float, Float32_num, FLOATINGLTR)
Float64_dtype = Dtype(cast_float64, unwrap_float, Float64_num, FLOATINGLTR)
Float96_dtype = Dtype(cast_float96, unwrap_float, Float96_num, FLOATINGLTR)

_dtype_list = (Bool_dtype,
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
)

def find_scalar_dtype(space, scalar):
    if space.is_true(space.isinstance(scalar, space.w_int)):
        return Long_dtype
    if space.is_true(space.isinstance(scalar, space.w_float)):
        return Float64_dtype

def get_dtype(space, w_type, w_string_or_type):
    if space.is_true(space.isinstance(w_string_or_type, space.gettypeobject(Dtype.typedef))):
        return w_string_or_type
    if space.is_true(space.isinstance(w_string_or_type, space.w_str)):
        s = space.str_w(w_string_or_type)
        if len(s) == 1:
            typenum = _letters_to_nums[ord(s)]
            dtype = _dtype_list[typenum]
            if typenum != -1 and dtype is not None:
                return _dtype_list[typenum]
        # XXX: need to put in 2 letters strings
        raise OperationError(space.w_ValueError,
                            space.wrap("type not recognized"))
    elif space.is_true(space.isinstance(w_string_or_type, space.w_type)):
        # XXX: need to implement this
        return Float64_dtype
    else:
        raise OperationError(space.w_TypeError,
                            space.wrap("data type not understood"))

def find_base_dtype(dtype1, dtype2):
    num1 = dtype1.num
    num2 = dtype2.num
    # this is much more complex
    if num1 < num2:
        return dtype2
    return dtype


def descr_new_dtype(space, w_type, w_string_or_type):
    return space.wrap(get_dtype(space, w_type, w_string_or_type))

Dtype.typedef = TypeDef(
    'numpy.dtype',
    __new__  = interp2app(descr_new_dtype),

    num = GetSetProperty(Dtype.descr_num),
    kind = GetSetProperty(Dtype.descr_kind),
)
