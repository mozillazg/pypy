from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.rlib.jit import dont_look_inside
from pypy.rlib import rgc
from pypy.rlib.unroll import unrolling_iterable

FloatArray = lltype.GcArray(lltype.Float)


class W_SizedFloatArray(Wrappable):
    @dont_look_inside
    def __init__(self, space, size):
        self.space = space
        self.size = size
        print "malloc"
        #self.buffer = lltype.malloc(rffi.DOUBLEP.TO, size, flavor='raw',
        #                            zero=True)
        #self.buffer = rgc.malloc_nonmovable(lltype.GcArray(lltype.Float),
        #                                    size)
        self.buffer = lltype.malloc(FloatArray, size, zero=True)
        print "buf: ", self.buffer

    def __del__(self):
        print "free"
        #lltype.free(self.buffer, flavor='raw')

    def descr_getitem(self, idx):
        return self.space.wrap(self.buffer[idx])
    descr_getitem.unwrap_spec = ['self', int]

    def descr_setitem(self, idx, val):
        self.buffer[idx] = val
    descr_setitem.unwrap_spec = ['self', int, float]

W_SizedFloatArray.typedef = TypeDef(
     'SizedFloatArray',
    __getitem__=interp2app(W_SizedFloatArray.descr_getitem),
     __setitem__=interp2app(W_SizedFloatArray.descr_setitem),
)


def sized_array(space, size):
    return W_SizedFloatArray(space, size)
sized_array.unwrap_spec = (ObjSpace, int)


class TypeCode(object):
    def __init__(self, itemtype, unwrap, canoverflow=False, signed=False):
        self.itemtype = itemtype
        if itemtype is lltype.SingleFloat:
            self.bytes = 4
        else:
            self.bytes = rffi.sizeof(itemtype)
        self.unwrap = unwrap
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
unroll_typecodes = unrolling_iterable(types.keys())


class W_Array(Wrappable):
    def __init__(self, space, typecode):
        if len(typecode) != 1:
            msg = 'array() argument 1 must be char, not str'
            raise OperationError(space.w_TypeError, space.wrap(msg))
        if typecode not in  'cbBuhHiIlLfd':
            msg = 'bad typecode (must be c, b, B, u, h, H, i, I, l, L, f or d)'
            raise OperationError(space.w_ValueError, space.wrap(msg))
        self.space = space
        self.typecode = typecode
        self.len = 0
        self.buffer = None
        self.itemsize = types[typecode].bytes

    def item_w(self, w_item):
        space = self.space
        for c in unroll_typecodes:
            if self.typecode == c:
                tc = types[c]
                unwrap = getattr(space, tc.unwrap)
                item = unwrap(w_item)
                if  tc.unwrap == 'bigint_w':
                    try:
                        if tc.signed:
                            item = item.tolonglong()
                        else:
                            item = item.toulonglong()
                    except (ValueError, OverflowError):
                        msg = 'unsigned %d-byte integer out of range' % tc.bytes
                        raise OperationError(space.w_OverflowError, space.wrap(msg))

                if tc.canoverflow:
                    msg = None
                    if tc.signed:
                        if item < -2 ** (tc.bytes * 8) / 2:
                            msg = 'signed %d-byte integer is less than minimum' % tc.bytes
                        elif item > 2 ** (tc.bytes * 8) / 2 - 1:
                            msg = 'signed %d-byte integer is greater than maximum' % tc.bytes
                    else:
                        if item < 0:
                            msg = 'unsigned %d-byte integer is less than minimum' % tc.bytes
                        elif item > 2 ** (tc.bytes * 8) - 1:
                            msg = 'unsigned %d-byte integer is greater than maximum' % tc.bytes
                    if msg is not None:
                        raise OperationError(space.w_OverflowError, space.wrap(msg))
                return rffi.cast(tc.itemtype, item)

    def setlen(self, size):
        new_buffer = lltype.malloc(lltype.GcArray(types[self.typecode].itemtype), size)
        for i in range(self.len):
            new_buffer[i] = self.buffer[i]
        self.buffer = new_buffer
        self.len = size

    def descr_append(self, w_x):
        x = self.item_w(w_x)
        self.setlen(self.len + 1)
        self.buffer[self.len - 1] = x
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

    def descr_getitem(self, w_idx):
        space=self.space
        start, stop, step = space.decode_index(w_idx, self.len)
        if step==0:
            item = self.buffer[start]
            if self.typecode in ('b', 'B', 'h', 'H', 'i', 'l'):
                item = rffi.cast(lltype.Signed, item)
            elif self.typecode == 'f':
                item = float(item)
            return self.space.wrap(item)
        else:
            size = (stop - start) / step
            if (stop - start) % step > 0: size += 1
            w_a=W_Array(self.space, self.typecode)
            w_a.setlen(size)
            j=0
            for i in range(start, stop, step):
                w_a.buffer[j]=self.buffer[i]
                j+=1
            return w_a
    descr_getitem.unwrap_spec = ['self', W_Root]

    def descr_setitem(self, w_idx, w_item):
        start, stop, step = self.space.decode_index(w_idx, self.len)
        if step==0:
            item = self.item_w(w_item)
            self.buffer[start] = item
        else:
            if isinstance(w_item, W_Array):
                if self.typecode == w_item.typecode:
                    size = (stop - start) / step
                    if (stop - start) % step > 0: size += 1
                    if w_item.len != size:
                        msg = ('attempt to assign array of size %d to ' + 
                               'slice of size %d') % (w_item.len, size)
                        raise OperationError(self.space.w_ValueError,
                                             self.space.wrap(msg))
                    j=0
                    for i in range(start, stop, step):
                        self.buffer[i]=w_item.buffer[j]
                        j+=1
                    return
            msg='can only assign array to array slice'
            raise OperationError(self.space.w_TypeError, self.space.wrap(msg))
                
    descr_setitem.unwrap_spec = ['self', W_Root, W_Root]

    def descr_len(self):
        return self.space.wrap(self.len)
    descr_len.unwrap_spec = ['self']

    def descr_fromstring(self, s):
        import struct
        if len(s)%self.itemsize !=0:
            msg = 'string length not a multiple of item size'
            raise OperationError(self.space.w_ValueError, self.space.wrap(msg))
        oldlen = self.len
        new = len(s) / self.itemsize
        self.setlen(oldlen + new)
        for i in range(new):
            p = i * self.itemsize
            item=struct.unpack(self.typecode, s[p:p + self.itemsize])[0]
            self.buffer[oldlen + i]=self.item_w(self.space.wrap(item))
    descr_fromstring.unwrap_spec = ['self', str]

    def descr_fromfile(self, w_f, n):
        space=self.space
        size = n*self.itemsize
        w_s = space.call_function(
            space.getattr(w_f, space.wrap('read')),
            space.wrap(size))
        s=space.str_w(w_s)
        if len(s) != size:
            n = len(s) % self.itemsize
            if n != 0: s = s[0:-(len(s) % self.itemsize)]
            self.descr_fromstring(s)
            msg='not enough items in file'
            raise OperationError(self.space.w_EOFError, self.space.wrap(msg))
        else:
            self.descr_fromstring(s)
    descr_fromfile.unwrap_spec = ['self', W_Root, int]

    def descr_fromlist(self, w_lst):
        space=self.space
        oldbuf = self.buffer
        oldlen = self.len
        try:
            new=space.int_w(space.len(w_lst))
            self.setlen(oldlen+new)
            for i in range(new):
                w_item=space.getitem(w_lst, space.wrap(i))
                self.buffer[oldlen + i] = self.item_w(w_item)
        except OperationError:
            self.buffer = oldbuf
            self.len = oldlen
            raise
    descr_fromlist.unwrap_spec = ['self', W_Root]

    def descr_fromunicode(self, s):
        if self.typecode != 'u':
            msg = "fromunicode() may only be called on type 'u' arrays"
            raise OperationError(self.space.w_ValueError, self.space.wrap(msg))
        self.descr_fromlist(self.space.wrap(s))
    descr_fromunicode.unwrap_spec = ['self', unicode]

        
            

def descr_itemsize(space, self):
    return space.wrap(self.itemsize)

W_Array.typedef = TypeDef(
    'Array',
    append      = interp2app(W_Array.descr_append),
    extend      = interp2app(W_Array.descr_extend),
    __len__     = interp2app(W_Array.descr_len),
    __getitem__ = interp2app(W_Array.descr_getitem),
    __setitem__ = interp2app(W_Array.descr_setitem),
    itemsize    = GetSetProperty(descr_itemsize, cls=W_Array),
    fromstring  = interp2app(W_Array.descr_fromstring),
    fromfile    = interp2app(W_Array.descr_fromfile),
    fromlist    = interp2app(W_Array.descr_fromlist),
    fromunicode = interp2app(W_Array.descr_fromunicode),
)


def array(space, typecode, w_initializer=None):
    a = W_Array(space, typecode)
    if w_initializer is not None:
        if space.is_w(space.type(w_initializer), space.w_str):
            a.descr_fromstring(space.str_w(w_initializer))
        elif space.is_w(space.type(w_initializer), space.w_unicode):
            a.descr_fromunicode(space.unicode_w(w_initializer))
        elif space.is_w(space.type(w_initializer), space.w_list):
            a.descr_fromlist(w_initializer)
        elif not space.is_w(w_initializer, space.w_None):
            a.descr_extend(w_initializer)  

    return a
array.unwrap_spec = (ObjSpace, str, W_Root)
