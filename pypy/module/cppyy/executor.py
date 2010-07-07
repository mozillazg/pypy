import pypy.module.cppyy.capi as capi

from pypy.rpython.lltypesystem import rffi, lltype

_executors = {}


class FunctionExecutor(object):
    def execute(self, space, func, num_args, args):
        raise NotImplementedError("abstract base class")


class LongExecutor(FunctionExecutor):
    def execute(self, space, func, cppthis, num_args, args):
        if cppthis is not None:
            result = capi.c_callmethod_l(func.cpptype.name, func.method_index, cppthis, num_args, args)
        else:
            result = capi.c_callstatic_l(func.cpptype.name, func.method_index, num_args, args)
        return space.wrap(result)

class DoubleExecutor(FunctionExecutor):
    def execute(self, space, func, cppthis, num_args, args):
        if cppthis is not None:
            raise NotImplementedError
        else:
            result = capi.c_callstatic_d(func.cpptype.name, func.method_index, num_args, args)
        return space.wrap(result)

class CStringExecutor(FunctionExecutor):
    def execute(self, space, func, cppthis, num_args, args):
        if cppthis is not None:
            raise NotImplementedError
        else:
            lresult = capi.c_callstatic_l(func.cpptype.name, func.method_index, num_args, args)
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

_executors["int"]                 = LongExecutor()
_executors["long"]                = LongExecutor()
_executors["double"]              = DoubleExecutor()
_executors["char*"]               = CStringExecutor()
