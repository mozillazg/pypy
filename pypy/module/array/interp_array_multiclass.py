from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.rlib.jit import dont_look_inside
from pypy.rlib import rgc

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

types = {
    'c': lltype.GcArray(lltype.Char),
    'u': lltype.GcArray(lltype.UniChar),
    'f': lltype.GcArray(lltype.SingleFloat),
    'd': lltype.GcArray(lltype.Float),
    }
## def array(space, typecode, w_initializer=None):
##     if 
##     self.len=0
##     self.buffer=None
##     if w_initializer is not None and not space.is_w(w_size, space.w_None):
##         self.extend(w_initializer) #FIXME: use fromlist, fromstring, ...
        
##     return W_SizedFloatArray(space, size)

class W_Array(Wrappable):
    def __init__(self, space, typecode):
        self.space=space
        self.typecode=typecode
        self.len=0
        self.buffer=None

    def item_w(self, w_item):
        if self.typecode == 'c':
            return self.space.str_w(w_item)
        elif self.typecode == 'u':
            self.space.unicode_w(w_item)
        elif self.typecode in ('b', 'B', 'h', 'H', 'i', 'l'):
            self.space.int_w(w_item)
        elif self.typecode in ('I', 'L'):
            self.space.long_w(w_item)
        elif self.typecode in ('f', 'd'):
            self.space.float_w(w_item)


    def setlen(self, size):
        new_buffer=lltype.malloc(types[self.typecode], size, zero=True)
        for i in range(self.len):
            new_buffer[i]=self.buffer[i]
        self.buffer=new_buffer
        self.len=size

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
            print w_item
            self.descr_append(space.str_w(w_item))
    descr_extend.unwrap_spec = ['self', W_Root]
        

    def descr_getitem(self, idx):
        return self.space.wrap(self.buffer[idx])
    descr_getitem.unwrap_spec = ['self', int]

class W_CharArray(W_Array):
    def descr_append(self,x):
        print x
        self.setlen(self.len+1)
        self.buffer[self.len-1]=x
    descr_append.unwrap_spec = ['self', str]

    def descr_setitem(self, idx, val):
        self.buffer[idx]=val
    descr_setitem.unwrap_spec = ['self', int, float]

    
class W_UnicodeArray(W_Array):
    def descr_append(self, x):
        self.setlen(self.len+1)
        self.buffer[self.len-1]=x
    descr_append.unwrap_spec = ['self', unicode]

class W_IntArray(W_Array):
    def descr_append():
        pass
    descr_append.unwrap_spec = ['self', int]

class W_LongArray(W_Array):
    def descr_append():
        pass
    descr_append.unwrap_spec = ['self', long]

class W_FloatArray(W_Array):
    def descr_append():
        pass
    descr_append.unwrap_spec = ['self', float]

def mktypedef(name, cls):
    methods={
        'append': interp2app(cls.descr_append),
        'extend': interp2app(cls.descr_extend),
        '__getitem__': interp2app(cls.descr_getitem),
        }
    cls.typedef = TypeDef(name, **methods)

mktypedef('CharArray', W_CharArray)
mktypedef('UnicodeArray', W_UnicodeArray)
    

def array(space, typecode, w_initializer=None):
    if len(typecode) != 1:
        msg='array() argument 1 must be char, not str'
        raise OperationError(space.w_TypeError,space.wrap(msg))
    if typecode == 'c':
        a=W_CharArray(space, typecode)
    elif typecode == 'u':
        a=W_UnicodeArray(space, typecode)
    elif typecode in ('b', 'B', 'h', 'H', 'i', 'l'):
        a=W_IntArray(space, typecode)
    elif typecode in ('I', 'L'):
        a=W_LongArray(space, typecode)
    elif typecode in ('f', 'd'):
        a=W_FloatArray(space, typecode)
    else:
        msg='bad typecode (must be c, b, B, u, h, H, i, I, l, L, f or d)'
        raise OperationError(space.w_ValueError,space.wrap(msg))

    if w_initializer is not None:
        if not space.is_w(w_initializer, space.w_None):
            a.descr_extend(w_initializer) #FIXME: use fromlist, fromstring, ...

    return a
    
array.unwrap_spec=(ObjSpace, str, W_Root)
    
