from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.rlib.jit import dont_look_inside
from pypy.rlib import rgc
from pypy.rlib.rbigint import rbigint

FloatArray=lltype.GcArray(lltype.Float)

class W_SizedFloatArray(Wrappable):
    @dont_look_inside
    def __init__(self, space, size):
        self.space=space
        self.size=size
        print "malloc"
        #self.buffer = lltype.malloc(rffi.DOUBLEP.TO, size, flavor='raw', zero=True)
        #self.buffer = rgc.malloc_nonmovable(lltype.GcArray(lltype.Float), size)
        self.buffer = lltype.malloc(FloatArray, size, zero=True)
        print "buf: ", self.buffer

    def __del__(self):
        print "free"
        #lltype.free(self.buffer, flavor='raw')

    def descr_getitem(self, idx):
        return self.space.wrap(self.buffer[idx])
    descr_getitem.unwrap_spec = ['self', int]
    
    def descr_setitem(self, idx, val):
        self.buffer[idx]=val
    descr_setitem.unwrap_spec = ['self', int, float]

W_SizedFloatArray.typedef = TypeDef(
     'SizedFloatArray',
     __getitem__ = interp2app(W_SizedFloatArray.descr_getitem),
     __setitem__ = interp2app(W_SizedFloatArray.descr_setitem),
)
        
def sized_array(space,size):
    return W_SizedFloatArray(space, size)
sized_array.unwrap_spec=(ObjSpace, int)


class TypeCode(object):
    def __init__(self, itemtype, unwrap, canoverflow=False, signed=False):
        self.itemtype=itemtype
        if itemtype is lltype.SingleFloat:
            self.bytes=4
        else:
            self.bytes = rffi.sizeof(itemtype)
        self.unwrap=unwrap
        self.signed = signed
        self.canoverflow = canoverflow
        


types = {
    'c': TypeCode(lltype.Char,        'str_w'),
    'u': TypeCode(lltype.UniChar,     'unicode_w'),
    'b': TypeCode(rffi.SIGNEDCHAR,    'int_w', True, True),
    'B': TypeCode(rffi.UCHAR,         'int_w', True),
    'h': TypeCode(rffi.SHORT,         'int_w', True, True),
    'H': TypeCode(rffi.USHORT,        'int_w', True),
    'i': TypeCode(rffi.INT,           'int_w', True, True),
    'I': TypeCode(rffi.UINT,          'int_w', True),
    'l': TypeCode(rffi.LONG,          'int_w', True, True),
    'L': TypeCode(rffi.ULONG,         'bigint_w', True),
    'f': TypeCode(lltype.SingleFloat, 'float_w'),
    'd': TypeCode(lltype.Float,       'float_w'),
    }

class W_Array(Wrappable):
    def __init__(self, space, typecode):
        if len(typecode) != 1:
            msg='array() argument 1 must be char, not str'
            raise OperationError(space.w_TypeError,space.wrap(msg))
        if typecode not in  'cbBuhHiIlLfd':
            msg='bad typecode (must be c, b, B, u, h, H, i, I, l, L, f or d)'
            raise OperationError(space.w_ValueError,space.wrap(msg))
        self.space=space
        self.typecode=typecode
        self.len=0
        self.buffer=None
        self.itemsize = types[typecode].bytes

    def item_w(self, w_item):        
        space=self.space
        tc=types[self.typecode]
        unwrap=getattr(space, tc.unwrap)
        item=unwrap(w_item)
        if  tc.unwrap=='bigint_w':
            try:
                if tc.signed: item=item.tolonglong()
                else: item=item.toulonglong()
            except (ValueError, OverflowError):
                msg='unsigned %d-byte integer out of range'%tc.bytes
                raise OperationError(space.w_OverflowError, space.wrap(msg))    

        if tc.canoverflow:
            msg=None
            if tc.signed:
                if item<-2**(tc.bytes*8)/2:
                    msg='signed %d-byte integer is less than minimum'%tc.bytes
                elif item>2**(tc.bytes*8)/2-1:
                    msg='signed %d-byte integer is greater than maximum'%tc.bytes
            else:
                if item<0:
                    msg='unsigned %d-byte integer is less than minimum'%tc.bytes
                elif item>2**(tc.bytes*8)-1:
                    msg='unsigned %d-byte integer is greater than maximum'%tc.bytes
            if msg is not None:
                raise OperationError(space.w_OverflowError, space.wrap(msg))
        return rffi.cast(tc.itemtype, item)

    def setlen(self, size):
        new_buffer=lltype.malloc(lltype.GcArray(types[self.typecode].itemtype), size)
        for i in range(self.len):
            new_buffer[i]=self.buffer[i]
        self.buffer=new_buffer
        self.len=size

    def descr_append(self,w_x):
        x=self.item_w(w_x)
        self.setlen(self.len+1)
        self.buffer[self.len-1]=x
    descr_append.unwrap_spec = ['self', W_Root]

    def descr_extend(self, w_initializer):
        space = self.space
        w_iterator = space.iter(w_initializer)
        while True:
            try:
                w_item = space.next(w_iterator)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break
            self.descr_append(w_item)
    descr_extend.unwrap_spec = ['self', W_Root]
        

    def descr_getitem(self, idx):
        item = self.buffer[idx]
        if self.typecode in ('b', 'B', 'h', 'H', 'i', 'l'):
            item=rffi.cast(lltype.Signed, item)
        if self.typecode == 'f':
            item=float(item)
        return self.space.wrap(item)
    descr_getitem.unwrap_spec = ['self', int]

    def descr_setitem(self, idx, w_item):
        item=self.item_w(w_item)
        self.buffer[idx]=item
    descr_setitem.unwrap_spec = ['self', int, W_Root]
    
    def descr_len(self):
        return self.space.wrap(self.len)
    descr_len.unwrap_spec = ['self']

    def descr_fromstring(self, s):
        import struct
        

def descr_itemsize(space, self):
    return space.wrap(self.itemsize)

W_Array.typedef=TypeDef(
    'Array',
    append      = interp2app(W_Array.descr_append),
    extend      = interp2app(W_Array.descr_extend),
    __len__     = interp2app(W_Array.descr_len),
    __getitem__ = interp2app(W_Array.descr_getitem),
    __setitem__ = interp2app(W_Array.descr_setitem),
    itemsize    = GetSetProperty(descr_itemsize, cls=W_Array)
)

def array(space, typecode, w_initializer=None):
    a=W_Array(space, typecode)
    if w_initializer is not None:
        if not space.is_w(w_initializer, space.w_None):
            a.descr_extend(w_initializer) #FIXME: use fromlist, fromstring, ...

    return a
    
array.unwrap_spec=(ObjSpace, str, W_Root)
    
