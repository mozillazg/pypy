from pypy.interpreter.error import OperationError

class CallLikelyBuiltinMixin(object):
    _mixin_ = True

    def CALL_LIKELY_BUILTIN(f, oparg):
        from pypy.module.__builtin__ import OPTIMIZED_BUILTINS, Module
        from pypy.objspace.std.dictmultiobject import W_DictMultiObject
        w_globals = f.w_globals
        num = oparg >> 8
        assert isinstance(w_globals, W_DictMultiObject)
        w_value = w_globals.implementation.get_builtin_indexed(num)
        if w_value is None:
            w_builtins = f.builtin
            assert isinstance(w_builtins, Module)
            w_builtin_dict = w_builtins.w_dict
            assert isinstance(w_builtin_dict, W_DictMultiObject)
            w_value = w_builtin_dict.implementation.get_builtin_indexed(num)
##                 if w_value is not None:
##                     print "CALL_LIKELY_BUILTIN fast"
        if w_value is None:
            varname = OPTIMIZED_BUILTINS[num]
            message = "global name '%s' is not defined" % varname
            raise OperationError(f.space.w_NameError,
                                 f.space.wrap(message))
        nargs = oparg & 0xff
        w_function = w_value
        try:
            w_result = f.space.call_valuestack(w_function, nargs, f.valuestack)
            # XXX XXX fix the problem of resume points!
            #rstack.resume_point("CALL_FUNCTION", f, nargs, returns=w_result)
        finally:
            f.valuestack.drop(nargs)
        f.valuestack.push(w_result)
