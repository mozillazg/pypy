from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import rffi, lltype

# for tests only
class W_Test(Wrappable):
    def __init__(self, space):
        self.space = space

    def get_intp_w(self, space, n, w_values):
        values_w = [ space.int_w(w_x) for w_x in space.listview(w_values) ]
        intp = lltype.malloc(rffi.INTP.TO, n, flavor='raw') # XXX free it!
        for i in xrange(n):
            intp[i] = values_w[i]
        return space.wrap(rffi.cast(lltype.Signed, intp))

    def get_charp_w(self, space, txt):
        charp = rffi.str2charp(txt)
        return space.wrap(rffi.cast(lltype.Signed, charp)) # XXX free it!

    def get_str_w(self, space, addr):
        charp = rffi.cast(rffi.CCHARP, addr)
        return space.wrap(rffi.charp2str(charp)) # XXX free it?

    def get_int_from_addr_w(self, space, addr):
        intp = rffi.cast(rffi.INTP, addr)
        return space.wrap(intp[0]) # return the first element

def W_Test___new__(space, w_x):
    return space.wrap(W_Test(space))

W_Test.typedef = TypeDef(
        'Test',
        __new__ = interp2app(W_Test___new__, unwrap_spec=[ObjSpace, W_Root]),
        get_intp = interp2app(W_Test.get_intp_w,
                              unwrap_spec=['self', ObjSpace, int, W_Root]),
        get_charp = interp2app(W_Test.get_charp_w,
                              unwrap_spec=['self', ObjSpace, str]),
        get_str = interp2app(W_Test.get_str_w,
                              unwrap_spec=['self', ObjSpace, int]),
        get_int_from_addr = interp2app(W_Test.get_int_from_addr_w,
                                 unwrap_spec=['self', ObjSpace, int])
)

