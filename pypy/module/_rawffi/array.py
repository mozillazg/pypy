
""" Interpreter-level implementation of array, exposing ll-structure
to app-level with apropriate interface
"""

from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable,\
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.module._rawffi.interp_rawffi import segfault_exception
from pypy.module._rawffi.interp_rawffi import W_DataInstance
from pypy.module._rawffi.interp_rawffi import unwrap_value, wrap_value, _get_type,\
     TYPEMAP
from pypy.rlib.rarithmetic import intmask

def push_elem(ll_array, pos, value):
    TP = lltype.typeOf(value)
    ll_array = rffi.cast(lltype.Ptr(rffi.CArray(TP)), ll_array)
    ll_array[pos] = value
push_elem._annspecialcase_ = 'specialize:argtype(2)'

def get_elem(ll_array, pos, ll_t):
    ll_array = rffi.cast(lltype.Ptr(rffi.CArray(ll_t)), ll_array)
    return ll_array[pos]
get_elem._annspecialcase_ = 'specialize:arg(2)'

class W_Array(Wrappable):
    def __init__(self, space, of):
        self.space = space
        self.of = of
        self.itemsize = intmask(TYPEMAP[of].c_size)

    def allocate(self, space, length):
        return W_ArrayInstance(space, self, length)

    def descr_call(self, space, length, w_iterable=None):
        result = self.allocate(space, length)
        if not space.is_w(w_iterable, space.w_None):
            items_w = space.unpackiterable(w_iterable)
            iterlength = len(items_w)
            if iterlength > length:
                raise OperationError(space.w_ValueError,
                                     space.wrap("too many items for specified"
                                                " array length"))
            for num in range(iterlength):
                w_item = items_w[num]
                unwrap_value(space, push_elem, result.ll_buffer, num, self.of,
                             w_item)
        return space.wrap(result)

    def fromaddress(self, space, address, length):
        return space.wrap(W_ArrayInstance(space, self, length, address))
    fromaddress.unwrap_spec = ['self', ObjSpace, int, int]

class ArrayCache:
    def __init__(self, space):
        self.space = space
        self.cache = {}
        self.array_of_ptr = self.get_array_type('P')

    def get_array_type(self, of):
        try:
            return self.cache[of]
        except KeyError:
            _get_type(self.space, of)
            result = W_Array(self.space, of)
            self.cache[of] = result
            return result

def get_array_cache(space):
    return space.fromcache(ArrayCache)

def descr_new_array(space, w_type, of):
    array_type = get_array_cache(space).get_array_type(of)
    return space.wrap(array_type)

W_Array.typedef = TypeDef(
    'Array',
    __new__  = interp2app(descr_new_array, unwrap_spec=[ObjSpace, W_Root, str]),
    __call__ = interp2app(W_Array.descr_call,
                          unwrap_spec=['self', ObjSpace, int, W_Root]),
    fromaddress = interp2app(W_Array.fromaddress),
    of = interp_attrproperty('of', W_Array),
)
W_Array.typedef.acceptable_as_base_class = False


class W_ArrayInstance(W_DataInstance):
    def __init__(self, space, shape, length, address=0):
        W_DataInstance.__init__(self, space, shape.itemsize * length, address)
        self.length = length
        self.shape = shape

    # XXX don't allow negative indexes, nor slices

    def setitem(self, space, num, w_value):
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        unwrap_value(space, push_elem, self.ll_buffer, num, self.shape.of,
                     w_value)
    setitem.unwrap_spec = ['self', ObjSpace, int, W_Root]

    def getitem(self, space, num):
        if num >= self.length or num < 0:
            raise OperationError(space.w_IndexError, space.w_None)
        return wrap_value(space, get_elem, self.ll_buffer, num, self.shape.of)
    getitem.unwrap_spec = ['self', ObjSpace, int]

W_ArrayInstance.typedef = TypeDef(
    'ArrayInstance',
    __setitem__ = interp2app(W_ArrayInstance.setitem),
    __getitem__ = interp2app(W_ArrayInstance.getitem),
    buffer      = GetSetProperty(W_ArrayInstance.getbuffer),
    shape       = interp_attrproperty('shape', W_ArrayInstance),
    free        = interp2app(W_ArrayInstance.free),
    byptr       = interp2app(W_ArrayInstance.byptr),
)
W_ArrayInstance.typedef.acceptable_as_base_class = False
