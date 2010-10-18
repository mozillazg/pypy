from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rffi

from sys import byteorder

byteorder = '>' if byteorder == 'big' else '<'

class TypeDescr(Wrappable):
    def __init__(self, dtype, name):
        self.dtype = dtype
        self.name = name
        self.w_native_type = None

    def descr_eq(self, space, w_type):
        if isinstance(w_type, TypeDescr):
            other_type = w_type.dtype
        else:
            other_type = get(space, w_type)

        typecode = self.dtype.typecode
        other_typecode = other_type.typecode

        return space.w_True if typecode == other_typecode else space.w_False
    descr_eq.unwrap_spec = ['self', ObjSpace, W_Root]

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.name)
    descr_repr.unwrap_spec = ['self', ObjSpace]

def dtype_descr_itemsize(space, self):
    return space.wrap(self.dtype.itemsize())

TypeDescr.typedef = TypeDef('dtype',
                            itemsize = GetSetProperty(dtype_descr_itemsize, cls=TypeDescr),
                            __eq__ = interp2app(TypeDescr.descr_eq),
                            __repr__ = interp2app(TypeDescr.descr_repr),
                           )

storage_type = lltype.Ptr(rffi.CArray(lltype.Char))                           
null_data = lltype.nullptr(storage_type.TO)

class DescrBase(object): pass

_typeindex = {}
_descriptors = []
_w_descriptors = []
def descriptor(code, name, ll_type):
    arraytype = rffi.CArray(ll_type)
    class DescrImpl(DescrBase):
        def __init__(self):
            self.typeid = 0
            self.typecode = code

        def wrap(self, space, value):
            return space.wrap(value)

        def w_getitem(self, space, data, index):
            return space.wrap(self.getitem(data, index))

        def w_setitem(self, space, data, index, w_value):
            value = self.coerce_w(space, w_value)
            self.setitem(data, index, value)

        def itemsize(self):
            return rffi.sizeof(ll_type)

        def getitem(self, data, index):
            array = rffi.cast(lltype.Ptr(arraytype), data)
            return array[index]

        def setitem(self, data, index, value):
            array = rffi.cast(lltype.Ptr(arraytype), data)
            array[index] = value

        def alloc(self, count):
            mem = lltype.malloc(arraytype, count, flavor='raw')
            return rffi.cast(storage_type, mem)

        def free(self, data):
            lltype.free(data, flavor='raw')

        def wrappable_dtype(self):
            assert _w_descriptors[self.typeid].dtype is self, "This better be true."
            return _w_descriptors[self.typeid]

        def cast(self, data):
            return rffi.cast(lltype.Ptr(arraytype), data)

        def dump(self, data, count):
            data = self.cast(data)
            return ', '.join([str(data[i]) for i in range(count)])

        def typestr(self):
            if self is float_descr:
                code = 'f'
            else:
                code = self.typecode

            return ''.join([byteorder, code, str(self.itemsize())])

    for type in [lltype.Signed, lltype.Float]:
        def get_type(self, data, index):
            value = self.getitem(data, index)
            return rffi.cast(type, value)
        get_type.__name__ = 'get_%s' % type
        setattr(DescrImpl, 'get_%s' % type, get_type)

        def set_type(self, data, index, value):
            value = rffi.cast(ll_type, value)
            self.setitem(data, index, value)
        set_type.__name__ = 'set_%s' % type
        setattr(DescrImpl, 'set_%s' % type, set_type)

    DescrImpl.__name__ = 'Descr_%s' % name # XXX
                                
    typeid = len(_descriptors)

    _typeindex[code] = typeid
    descriptor = DescrImpl()
    descriptor.typeid = typeid

    _descriptors.append(descriptor)

    w_descriptor = TypeDescr(descriptor, name)
    _w_descriptors.append(w_descriptor)

    return descriptor

_typestring = {}
# int, int32 is l
# i is ??

int_descr = descriptor('i', 'int32', lltype.Signed)
IntDescrImpl = type(int_descr)
IntDescrImpl.unwrap = lambda self, space, value: space.int_w(value)
IntDescrImpl.coerce = lambda self, space, value: space.int(value)
IntDescrImpl.coerce_w = lambda self, space, value: space.int_w(space.int(value))
_int_index = _typeindex['i']
_typestring['int32'] = _int_index
w_int_descr = _w_descriptors[_int_index]

float_descr = descriptor('d', 'float64', lltype.Float)
FloatDescrImpl = type(float_descr)
FloatDescrImpl.unwrap = lambda self, space, value: space.float_w(value)
FloatDescrImpl.coerce = lambda self, space, value: space.float(value)
FloatDescrImpl.coerce_w = lambda self, space, value: space.float_w(space.float(value))
_float_index = _typeindex['d']
_typestring['float64'] = _float_index
w_float_descr = _w_descriptors[_float_index]

_result_types = {(_int_index, _int_index): _int_index,
                 (_int_index, _float_index): _float_index,
                 (_float_index, _int_index): _float_index,
                 (_float_index, _float_index): _float_index,
                }

def result(a, b):
    assert isinstance(a, DescrBase)
    assert isinstance(b, DescrBase)
    a = a.typeid
    b = b.typeid
    c = _result_types[(a, b)]
    return _descriptors[c]

def w_result(w_a, w_b):
    assert isinstance(w_a, TypeDescr)
    assert isinstance(w_b, TypeDescr)
    return result(w_a.dtype, w_b.dtype).wrappable_dtype()

def from_typecode(s):
    index = _typeindex[s]
    return _descriptors[index]

def from_typestring(s):
    index = _typestring[s]
    return _descriptors[index]

def from_wrapped_type(space, w_type):
    if w_type is space.w_int:
        return int_descr
    elif w_type is space.w_float:
        return float_descr #XXX: only handles two types!
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("unknown type %s" % w_type))

def get(space, w_dtype):
    if isinstance(w_dtype, TypeDescr):
        return w_dtype.dtype #FIXME: a little wasteful since we end up just getting the TypeDescr

    try:
        s = space.str_w(w_dtype)

        try:
            return from_typecode(s)
        except KeyError, e:
            return from_typestring(s)

    except KeyError, e:
        raise OperationError(space.w_TypeError,
                             space.wrap("data type not understood")
                            )

    except OperationError, e:
        if e.match(space, space.w_TypeError): pass # XXX: ValueError?

    return from_wrapped_type(space, w_dtype)

# FIXME: watch for wrapped typedescrs!
def infer_from_iterable(space, w_xs):
    highest_type = None
    dtype = None
    w_i = space.iter(w_xs)
    try:
        while True:
            w_element = space.next(w_i)      
            try:
                dtype = infer_from_iterable(space, w_element)
            except OperationError, e:
                if e.match(space, space.w_TypeError): # not iterable?
                    w_type = space.type(w_element)
                    dtype = from_wrapped_type(space, w_type)
                else: raise

            if highest_type is not None:
                a = highest_type.typeid   
                b = dtype.typeid
                highest_typeid = _result_types[(a, b)]
                highest_type = _descriptors[highest_typeid]
            else:
                highest_type = dtype
    except OperationError, e:
        if e.match(space, space.w_StopIteration):
            return highest_type
    else: raise
