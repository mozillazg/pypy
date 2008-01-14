
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import *
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.unroll import unrolling_iterable

from pypy.module.struct.standardfmttable import min_max_acc_method
from pypy.module.struct.nativefmttable import native_fmttable
from pypy.tool.sourcetools import func_with_new_name

class FfiValueError(Exception):
    def __init__(self, msg):
        self.msg = msg


def _signed_type_for(TYPE):
    sz = rffi.sizeof(TYPE)
    if sz == 4:   return ffi_type_sint32
    elif sz == 8: return ffi_type_sint64
    else: raise ValueError("unsupported type size for %r" % (TYPE,))

def _unsigned_type_for(TYPE):
    sz = rffi.sizeof(TYPE)
    if sz == 4:   return ffi_type_uint32
    elif sz == 8: return ffi_type_uint64
    else: raise ValueError("unsupported type size for %r" % (TYPE,))

TYPEMAP = {
    # XXX A mess with unsigned/signed/normal chars :-/
    'c' : ffi_type_uchar,
    'b' : ffi_type_schar,
    'B' : ffi_type_uchar,
    'h' : ffi_type_sshort,
    'H' : ffi_type_ushort,
    'i' : ffi_type_sint,
    'I' : ffi_type_uint,
    # xxx don't use ffi_type_slong and ffi_type_ulong - their meaning
    # changes from a libffi version to another :-((
    'l' : _signed_type_for(rffi.LONG),
    'L' : _unsigned_type_for(rffi.ULONG),
    'q' : _signed_type_for(rffi.LONGLONG),
    'Q' : _unsigned_type_for(rffi.ULONGLONG),
    'f' : ffi_type_float,
    'd' : ffi_type_double,
    's' : ffi_type_pointer,
    'P' : ffi_type_pointer,
    'z' : ffi_type_pointer,
    'O' : ffi_type_pointer,
}
TYPEMAP_PTR_LETTERS = "POsz"

LL_TYPEMAP = {
    'c' : rffi.CHAR,
    'b' : rffi.SIGNEDCHAR,
    'B' : rffi.UCHAR,
    'h' : rffi.SHORT,
    'H' : rffi.USHORT,
    'i' : rffi.INT,
    'I' : rffi.UINT,
    'l' : rffi.LONG,
    'L' : rffi.ULONG,
    'q' : rffi.LONGLONG,
    'Q' : rffi.ULONGLONG,
    'f' : rffi.FLOAT,
    'd' : rffi.DOUBLE,
    's' : rffi.CCHARP,
    'z' : rffi.CCHARP,
    'O' : rffi.VOIDP,
    'P' : rffi.VOIDP,
    'v' : lltype.Void,
}

def _get_type(space, key):
    try:
        return TYPEMAP[key]
    except KeyError:
        raise OperationError(space.w_ValueError, space.wrap(
            "Uknown type letter %s" % (key,)))
    return lltype.nullptr(FFI_TYPE_P.TO)

def _w_get_type(space, key):
    _get_type(space, key)
    return space.w_None
_w_get_type.unwrap_spec = [ObjSpace, str]

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.cdll = CDLL(name)
        self.name = name
        self.w_cache = space.newdict()
        self.space = space

    def get_type(self, key):
        space = self.space
        return _get_type(space, key)

    def ptr(self, space, name, w_argtypes, w_restype):
        """ Get a pointer for function name with provided argtypes
        and restype
        """
        if space.is_w(w_restype, space.w_None):
            restype = 'v'
            ffi_restype = ffi_type_void
        else:
            restype = space.str_w(w_restype)
            ffi_restype = self.get_type(restype)
        w = space.wrap
        w_argtypes = space.newtuple(space.unpackiterable(w_argtypes))
        w_key = space.newtuple([w(name), w_argtypes, w(restype)])
        try:
            return space.getitem(self.w_cache, w_key)
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                pass
            else:
                raise
        argtypes_w = space.unpackiterable(w_argtypes)
        argtypes = [space.str_w(w_arg) for w_arg in argtypes_w]
        ffi_argtypes = [self.get_type(arg) for arg in argtypes]
        try:
            ptr = self.cdll.getrawpointer(name, ffi_argtypes, ffi_restype)
            w_funcptr = W_FuncPtr(space, ptr, argtypes, restype)
            space.setitem(self.w_cache, w_key, w_funcptr)
            return w_funcptr
        except KeyError:
            raise OperationError(space.w_AttributeError, space.wrap(
                "No symbol %s found in library %s" % (name, self.name)))
    ptr.unwrap_spec = ['self', ObjSpace, str, W_Root, W_Root]

def descr_new_cdll(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_cdll.unwrap_spec = [ObjSpace, W_Root, str]

W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    ptr         = interp2app(W_CDLL.ptr),
    __doc__     = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it). On such a library you can call:
lib.ptr(func_name, argtype_list, restype)

where argtype_list is a list of single characters and restype is a single
character. The character meanings are more or less the same as in the struct
module, except that s has trailing \x00 added, while p is considered a raw
buffer."""
)

def pack_pointer(space, add_arg, argdesc, w_arg, push_func):
    arg = space.str_w(w_arg)
    ll_str = lltype.malloc(rffi.CCHARP.TO, len(arg), flavor='raw')
    for i in range(len(arg)):
        ll_str[i] = arg[i]
    push_func(add_arg, argdesc, ll_str)
    return ll_str

def make_size_checker(format, size, signed):
    min, max, _ = min_max_acc_method(size, signed)

    def checker(value):
        if value < min:
            raise FfiValueError("%d too small for format %s" % (value, format))
        elif value > max:
            raise FfiValueError("%d too large for format %s" % (value, format))
    return checker

_SIZE_CHECKERS = {
    'b' : True,
    'B' : False,
    'h' : True,
    'H' : False,
    'i' : True,
    'I' : False,
    'l' : True,
    'L' : False,
    'q' : True,
    'Q' : False,
}

# XXX check for single float as well
SIZE_CHECKERS = {}
for c, signed in _SIZE_CHECKERS.items():
    SIZE_CHECKERS[c] = make_size_checker(c, native_fmttable[c]['size'], signed)
unroll_size_checkers = unrolling_iterable(SIZE_CHECKERS.items())

def segfault_exception(space, reason):
    w_mod = space.getbuiltinmodule("_rawffi")
    w_exception = space.getattr(w_mod, space.wrap("SegfaultException"))
    return OperationError(w_exception, space.wrap(reason))


class W_DataInstance(Wrappable):
    def __init__(self, space, size, address=0):
        if address != 0:
            self.ll_buffer = rffi.cast(rffi.VOIDP, address)
        else:
            self.ll_buffer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw',
                                           zero=True)

    def getbuffer(space, self):
        return space.wrap(rffi.cast(rffi.INT, self.ll_buffer))

    def byptr(self, space):
        from pypy.module._rawffi.array import get_array_cache
        array_of_ptr = get_array_cache(space).array_of_ptr
        array = array_of_ptr.allocate(space, 1)
        array.setitem(space, 0, space.wrap(self))
        return space.wrap(array)
    byptr.unwrap_spec = ['self', ObjSpace]

    def free(self, space):
        if not self.ll_buffer:
            raise segfault_exception(space, "freeing NULL pointer")
        lltype.free(self.ll_buffer, flavor='raw')
        self.ll_buffer = lltype.nullptr(rffi.VOIDP.TO)
    free.unwrap_spec = ['self', ObjSpace]


def unwrap_value(space, push_func, add_arg, argdesc, tp, w_arg):
    w = space.wrap
    if tp == "d":
        push_func(add_arg, argdesc, space.float_w(w_arg))
    elif tp == "f":
        push_func(add_arg, argdesc, rffi.cast(rffi.FLOAT,
                                              space.float_w(w_arg)))
    elif tp in TYPEMAP_PTR_LETTERS:
        # check for NULL ptr
        if space.is_true(space.isinstance(w_arg, space.w_int)):
            push_func(add_arg, argdesc, rffi.cast(rffi.VOIDP, space.int_w(w_arg)))
        else:
            datainstance = space.interp_w(W_DataInstance, w_arg)
            push_func(add_arg, argdesc, datainstance.ll_buffer)
    elif tp == "c":
        s = space.str_w(w_arg)
        if len(s) != 1:
            raise OperationError(space.w_TypeError, w(
                "Expected string of length one as character"))
        val = s[0]
        push_func(add_arg, argdesc, val)
    else:
        for c, checker in unroll_size_checkers:
            if tp == c:
                if c == "q":
                    val = space.r_longlong_w(w_arg)
                elif c == "Q":
                    val = space.r_ulonglong_w(w_arg)
                elif c == "I" or c == "L" or c =="B":
                    val = space.uint_w(w_arg)
                else:
                    val = space.int_w(w_arg)
                try:
                    checker(val)
                except FfiValueError, e:
                    raise OperationError(space.w_ValueError, w(e.msg))
                TP = LL_TYPEMAP[c]
                push_func(add_arg, argdesc, rffi.cast(TP, val))
    
unwrap_value._annspecialcase_ = 'specialize:arg(1)'

ll_typemap_iter = unrolling_iterable(LL_TYPEMAP.items())

def wrap_value(space, func, add_arg, argdesc, tp):
    for c, ll_type in ll_typemap_iter:
        if tp == c:
            if c == 's' or c == 'z':
                ptr = func(add_arg, argdesc, rffi.CCHARP)
                if not ptr:
                    return space.w_None
                return space.wrap(rffi.charp2str(ptr))
            elif c == 'P' or c == 'O':
                res = func(add_arg, argdesc, rffi.VOIDP)
                if not res:
                    return space.w_None
                return space.wrap(rffi.cast(rffi.INT, res))
            elif c == 'v':
                func(add_arg, argdesc, ll_type)
                return space.w_None
            elif c == 'q' or c == 'Q' or c == 'L':
                return space.wrap(func(add_arg, argdesc, ll_type))
            elif c == 'f' or c == 'd':
                return space.wrap(float(func(add_arg, argdesc, ll_type)))
            elif c == 'c':
                return space.wrap(chr(rffi.cast(rffi.INT, func(add_arg, argdesc,
                                                               ll_type))))
            elif c == 'h' or c == 'H':
                return space.wrap(rffi.cast(rffi.INT, func(add_arg, argdesc,
                                                           ll_type)))
            else:
                return space.wrap(intmask(func(add_arg, argdesc, ll_type)))
    return space.w_None
wrap_value._annspecialcase_ = 'specialize:arg(1)'

def ptr_call(ptr, some_arg, ll_type):
    return ptr.call(ll_type)
ptr_call._annspecialcase_ = 'specialize:arg(2)'

def push(ptr, argdesc, value):
    ptr.push_arg(value)
push._annspecialcase_ = 'specialize:argtype(2)'

class W_FuncPtr(Wrappable):
    def __init__(self, space, ptr, argtypes, restype):
        from pypy.module._rawffi.array import get_array_cache
        self.ptr = ptr
        cache = get_array_cache(space)
        self.resarray = cache.get_array_type(restype)
        self.argtypes = argtypes

    def call(self, space, args_w):
        from pypy.module._rawffi.array import W_ArrayInstance
        argnum = len(args_w)
        if argnum != len(self.argtypes):
            msg = "Wrong number of argument: expected %d, got %d" % (
                len(self.argtypes), argnum)
            raise OperationError(space.w_TypeError, space.wrap(msg))
        args_ll = []
        for i in range(argnum):
            argtype = self.argtypes[i]
            w_arg = args_w[i]
            arg = space.interp_w(W_ArrayInstance, w_arg)
            if arg.shape.of != argtype:
                msg = "Argument %d should be typecode %s, got %s" % (
                    i+1, argtype, arg.shape.of)
                raise OperationError(space.w_TypeError, space.wrap(msg))
            args_ll.append(arg.ll_buffer)
            # XXX we could avoid the intermediate list args_ll
        result = self.resarray.allocate(space, 1)
        self.ptr.call(args_ll, result.ll_buffer)
        return space.wrap(result)
    call.unwrap_spec = ['self', ObjSpace, 'args_w']

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __call__ = interp2app(W_FuncPtr.call)
)

def _create_new_accessor(func_name, name):
    def accessor(space, tp_letter):
        if len(tp_letter) != 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "Expecting string of length one"))
        tp_letter = tp_letter[0] # fool annotator
        try:
            return space.wrap(intmask(getattr(TYPEMAP[tp_letter], name)))
        except KeyError:
            raise OperationError(space.w_ValueError, space.wrap(
                "Unknown type specification %s" % tp_letter))
    accessor.unwrap_spec = [ObjSpace, str]
    return func_with_new_name(accessor, func_name)

sizeof = _create_new_accessor('sizeof', 'c_size')
alignment = _create_new_accessor('alignment', 'c_alignment')
