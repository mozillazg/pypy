from pypy.rlib import rjitffi
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import rffi, lltype

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.space = space
        self.rcdll = rjitffi.CDLL(name, load=False)
        try:
            self.lib_w = W_LibHandler(self.space, name)
        except OSError, e:
            raise OperationError(space.w_OSError, space.wrap(str(e)))

    def get_w(self, space, func, w_args_type, res_type='v'):
        args_type_w = [ space.str_w(w_x)
                        for w_x in space.listview(w_args_type) ]
        try:
            ret = W_Get(space, self.rcdll.cpu, self.lib_w,
                        func, args_type_w, res_type)
        except ValueError, e:
            raise OperationError(space.w_ValueError, space.wrap(str(e)))
        return space.wrap(ret)

def W_CDLL___new__(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)

W_CDLL.typedef = TypeDef(
        'CDLL',
        __new__ = interp2app(W_CDLL___new__,unwrap_spec=[ObjSpace,W_Root,str]),
        get     = interp2app(W_CDLL.get_w, unwrap_spec=['self',
                                                        ObjSpace, str, W_Root, str]),
        __doc__ = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it)."""
)


class W_LibHandler(Wrappable):
    def __init__(self, space, name):
        self.space = space
        try:
            self.rlibhandler = rjitffi._LibHandler(name)
        except OSError, e:
            raise OperationError(space.w_OSError, space.wrap(str(e)))
        self.handler = self.rlibhandler.handler

def W_LibHandler___new__(space, w_type, name):
    try:
        return space.wrap(W_LibHandler(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)

W_LibHandler.typedef = TypeDef(
        'LibHandler',
        __new__ = interp2app(W_LibHandler___new__, unwrap_spec=[ObjSpace,
                                                                W_Root, str])
)

class Cache(object):
    def __init__(self, space):
        self.cache = {}

class W_Get(Wrappable):
    def __init__(self, space, cpu, lib, func, args_type, res_type='v'):
        self.space = space

        wrap_func = (self.wrap_int_w, self.wrap_float_w,
                     self.wrap_ref_w, self.wrap_void_w)
        self.rget = rjitffi._Get(cpu, lib, func, args_type, res_type,
                                 wrap_func, cache=True)

        # grab from the cache if possible
        arg_classes = ''.join(args_type)
        key = (res_type, arg_classes)
        cache = space.fromcache(Cache).cache
        try:
            self.rget.looptoken = cache[key]
        except KeyError:
            self.rget.gen_looptaken()
            cache[key] = self.rget.looptoken

    def call_w(self, space, w_args=None):
        if not space.is_w(w_args, space.w_None):
            i = 0
            w_iterator = space.iter(w_args)
            while True:
                try:
                    w_arg = space.next(w_iterator)
                except OperationError, e:
                    if not e.match(space, space.w_StopIteration):
                        raise
                    break # done

                if self.rget.args_type[i] == 'i':
                    self.rget.push_int(space.int_w(w_arg))
                elif self.rget.args_type[i] == 'f':
                    self.rget.push_float(space.float_w(w_arg))
                elif self.rget.args_type[i] == 'p':
                    self.rget.push_ref(space.int_w(w_arg))
                else:
                    # should never happen (raised earlier)
                    raise OperationError(
                            space.w_ValueError,
                            space.wrap('Unsupported type of argument: %s'
                                        % self.rget.args_type[0]))
                i += 1
        return self.rget.call()

    def wrap_int_w(self, value):
        return self.space.wrap(value)

    def wrap_float_w(self, value):
        return self.space.wrap(value)

    def wrap_ref_w(self, value):
        return self.space.wrap(value)

    def wrap_void_w(self, w_value):
        return w_value

#def W_Get___new__(space, w_type, cpu, lib, func, args_type, res_type):
#    try:
#        return space.wrap(W_Get(space, w_type, cpu, lib, func, args_type, res_type))
#    except OSError, e:
#        raise wrap_oserror(space, e)

W_Get.typedef = TypeDef(
        'Get',
        #__new__ = interp2app(W_Get___new__, unwrap_spec=[ObjSpace, W_Root, W_Root, W_Root, str, W_Root, str]),
        call = interp2app(W_Get.call_w, unwrap_spec=['self', ObjSpace, W_Root]),
        wrap_int = interp2app(W_Get.wrap_int_w, unwrap_spec=['self', int]),
        wrap_float = interp2app(W_Get.wrap_float_w, unwrap_spec=['self', float]),
        wrap_ref = interp2app(W_Get.wrap_ref_w, unwrap_spec=['self', int]),
        wrap_void = interp2app(W_Get.wrap_void_w, unwrap_spec=['self', W_Root])
)

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
