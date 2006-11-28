class CallLikelyBuiltinMixin(object):
    _mixin_ = True

    def CALL_LIKELY_BUILTIN(f, oparg):
        from pypy.module.__builtin__ import OPTIMIZED_BUILTINS, Module
        from pypy.objspace.std.warydictobject import W_WaryDictObject
        w_globals = f.w_globals
        num = oparg >> 8
        if (isinstance(w_globals, W_WaryDictObject) and
            not w_globals.shadowed[num]):
            w_builtins = f.builtin
            assert isinstance(w_builtins, Module)
            print "fast CALL_LIKELY_BUILTIN"
            w_value = w_builtins.builtins_by_index[num]
        else:
            w_varname = f.space.wrap(OPTIMIZED_BUILTINS[num])
            w_value = f.space.finditem(f.w_globals, w_varname)
            if w_value is None:
                # not in the globals, now look in the built-ins
                w_value = f.builtin.getdictvalue(f.space, w_varname)
                if w_value is None:
                    varname = f.getname_u(nameindex)
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
