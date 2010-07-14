from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.rlib.jit import dont_look_inside
from pypy.rlib import rgc


FloatArray = lltype.GcArray(lltype.Float)


class W_SizedFloatArray(Wrappable):
    _immutable_fields_ = ['size', 'buffer']
    
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


def simple_array(space, size):
    return W_SizedFloatArray(space, size)
simple_array.unwrap_spec = (ObjSpace, int)
