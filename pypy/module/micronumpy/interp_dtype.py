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
Float128_num = 13

# dtype 'kinds'. Used to determine which operations can be performed on array
BOOLLTR = 'b'
FLOATINGLTR = 'f'
SIGNEDLTR = 'i'
UNSIGNEDLTR = 'u'

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

def cast_float(val):
    return rffi.cast(lltype.Float, val)

def unwrap_float(space, val):
    return space.float_w(space.float(val))

def cast_long(val):
    return rffi.cast(rffi.INT, val)

def unwrap_int(space, val):
    return space.int_w(space.int(val))

def cast_ulong(val):
    return rffi.cast(rffi.UINT, val)

Float64_dtype = Dtype(cast_float, unwrap_float, Float64_num,
                        FLOATINGLTR)
#Int32_dtype = Dtype(cast_int32, unwrap_int, Int32_num, SIGNEDLTR)
#UInt32_dtype = Dtype(cast_uint32, unwrap_int, UIn32_num, UNSIGNEDLTR)
Long_dtype = Dtype(cast_long, unwrap_int, Long_num, SIGNEDLTR)
ULong_dtype = Dtype(cast_ulong, unwrap_int, Long_num, UNSIGNEDLTR)

_dtype_list = [None] * 14
_dtype_list[Float64_num] = Float64_dtype
#_dtype_list[Int32_num] = Int32_dtype
#_dtype_list[UInt32_num] = UInt32_dtype
_dtype_list[Long_num] = Long_dtype
_dtype_list[ULong_num] = ULong_dtype

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


def descr_new_dtype(space, w_type, w_string_or_type):
    return space.wrap(get_dtype(space, w_type, w_string_or_type))

Dtype.typedef = TypeDef(
    'numpy.dtype',
    __new__  = interp2app(descr_new_dtype),

    num = GetSetProperty(Dtype.descr_num),
    kind = GetSetProperty(Dtype.descr_kind),
)
