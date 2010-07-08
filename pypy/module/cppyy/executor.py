import pypy.module.cppyy.capi as capi

from pypy.rpython.lltypesystem import rffi, lltype

_executors = {}


class FunctionExecutor(object):
    def execute(self, space, func, cppthis, num_args, args):
        raise NotImplementedError("abstract base class")


class VoidExecutor(object):
    def execute(self, space, func, cppthis, num_args, args):
        capi.c_cppyy_call_v(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.w_None

class LongExecutor(FunctionExecutor):
    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_cppyy_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

class DoubleExecutor(FunctionExecutor):
    def execute(self, space, func, cppthis, num_args, args):
        result = capi.c_cppyy_call_d(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        return space.wrap(result)

class CStringExecutor(FunctionExecutor):
    def execute(self, space, func, cppthis, num_args, args):
        lresult = capi.c_cppyy_call_l(func.cpptype.handle, func.method_index, cppthis, num_args, args)
        ccpresult = rffi.cast(rffi.CCHARP, lresult)
        result = capi.charp2str_free(ccpresult)
        return space.wrap(result)

def get_executor(name):
    try:
        return _executors[name]
    except KeyError:
        pass

    return None # currently used until proper lazy instantiation available in interp_cppyy
 
 #  raise TypeError("no clue what %s is" % name)

_executors["void"]                = VoidExecutor()
_executors["int"]                 = LongExecutor()
_executors["long"]                = LongExecutor()
_executors["double"]              = DoubleExecutor()
_executors["char*"]               = CStringExecutor()
