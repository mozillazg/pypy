from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.rlib.jit import dont_look_inside
from pypy.rlib import rgc
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rstruct.runpack import runpack

class W_ArrayBase(Wrappable):
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


class TypeCode(object):
    def __init__(self, itemtype, unwrap, canoverflow=False, signed=False):
        self.itemtype = itemtype
        if itemtype is lltype.SingleFloat:
            self.bytes = 4
        else:
            self.bytes = rffi.sizeof(itemtype)
        self.arraytype = lltype.GcArray(itemtype)
        self.unwrap = unwrap
        self.signed = signed
        self.canoverflow = canoverflow
        self.w_class = None


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
for k, v in types.items(): v.typecode=k
unroll_typecodes = unrolling_iterable(types.keys())

for thetypecode, thetype in types.items():
    class W_Array(W_ArrayBase):
        mytype = thetype
        def __init__(self, space):
            self.space = space
            self.len = 0
            self.buffer = None

        def item_w(self, w_item):
            space = self.space
            unwrap = getattr(space, self.mytype.unwrap)
            item = unwrap(w_item)
            if  self.mytype.unwrap == 'bigint_w':
                try:
                    if self.mytype.signed:
                        item = item.tolonglong()
                    else:
                        item = item.toulonglong()
                except (ValueError, OverflowError):
                    msg = 'unsigned %d-byte integer out of range' % self.mytype.bytes
                    raise OperationError(space.w_OverflowError, space.wrap(msg))

            if self.mytype.canoverflow:
                msg = None
                if self.mytype.signed:
                    if item < -2 ** (self.mytype.bytes * 8) / 2:
                        msg = 'signed %d-byte integer is less than minimum' % self.mytype.bytes
                    elif item > 2 ** (self.mytype.bytes * 8) / 2 - 1:
                        msg = 'signed %d-byte integer is greater than maximum' % self.mytype.bytes
                else:
                    if item < 0:
                        msg = 'unsigned %d-byte integer is less than minimum' % self.mytype.bytes
                    elif item > 2 ** (self.mytype.bytes * 8) - 1:
                        msg = 'unsigned %d-byte integer is greater than maximum' % self.mytype.bytes
                if msg is not None:
                    raise OperationError(space.w_OverflowError, space.wrap(msg))
            return rffi.cast(self.mytype.itemtype, item)


        def setlen(self, size):
            new_buffer = lltype.malloc(self.mytype.arraytype, size)
            for i in range(self.len):
                new_buffer[i] = self.buffer[i]
            self.buffer = new_buffer
            self.len = size


        def descr_len(self):
            return self.space.wrap(self.len)
        descr_len.unwrap_spec = ['self']


        def descr_getitem(self, w_idx):
            space=self.space
            start, stop, step = space.decode_index(w_idx, self.len)
            if step==0:
                item = self.buffer[start]
                if self.mytype.typecode in ('b', 'B', 'h', 'H', 'i', 'l'):
                    item = rffi.cast(lltype.Signed, item)
                elif self.mytype.typecode == 'f':
                    item = float(item)
                return self.space.wrap(item)
            else:
                size = (stop - start) / step
                if (stop - start) % step > 0: size += 1
                w_a=W_Array(self.space, self.mytype.typecode)
                w_a.setlen(size)
                j=0
                for i in range(start, stop, step):
                    w_a.buffer[j]=self.buffer[i]
                    j+=1
                return w_a
        descr_getitem.unwrap_spec = ['self', W_Root]

    W_Array.typedef = TypeDef(
        'ArrayType_'+thetypecode,
        append      = interp2app(W_Array.descr_append),
        extend      = interp2app(W_Array.descr_extend),
        __len__     = interp2app(W_Array.descr_len),
        __getitem__ = interp2app(W_Array.descr_getitem),
    )

    thetype.w_class = W_Array


def array(space, typecode, w_initializer=None):
    if len(typecode) != 1:
        msg = 'array() argument 1 must be char, not str'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    typecode=typecode[0]

    for tc in unroll_typecodes:
        if typecode == tc:
            a = types[tc].w_class(space)
            break
    else:
        msg = 'bad typecode (must be c, b, B, u, h, H, i, I, l, L, f or d)'
        raise OperationError(space.w_ValueError, space.wrap(msg))
        
    if w_initializer is not None:
        if not space.is_w(w_initializer, space.w_None):
            a.descr_extend(w_initializer)  
        ## if space.is_w(space.type(w_initializer), space.w_str):
        ##     a.descr_fromstring(space.str_w(w_initializer))
        ## elif space.is_w(space.type(w_initializer), space.w_unicode):
        ##     a.descr_fromunicode(space.unicode_w(w_initializer))
        ## elif space.is_w(space.type(w_initializer), space.w_list):
        ##     a.descr_fromlist(w_initializer)
        ## elif not space.is_w(w_initializer, space.w_None):
        ##     a.descr_extend(w_initializer)  

    return a
array.unwrap_spec = (ObjSpace, str, W_Root)
