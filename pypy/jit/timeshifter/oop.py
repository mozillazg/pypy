from pypy.jit.timeshifter import rvalue, rtimeshift
from pypy.jit.timeshifter.rcontainer import cachedtype, SegfaultException
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype
from pypy.tool.sourcetools import func_with_new_name
from pypy.translator import exceptiontransform
from pypy.translator.simplify import get_funcobj, get_functype

class Index:
    def __init__(self, n):
        self.n = n


class OopSpecDesc:
    __metaclass__ = cachedtype

    def __init__(self, RGenOp, rtyper, exceptiondesc, fnobj, can_raise):
        self.rtyper = rtyper
        ll_func = fnobj._callable
        FUNCTYPE = lltype.typeOf(fnobj)
        nb_args = len(FUNCTYPE.ARGS)

        self.can_raise = can_raise

        # parse the oopspec and fill in the arguments
        operation_name, args = ll_func.oopspec.split('(', 1)
        assert args.endswith(')')
        args = args[:-1] + ','     # trailing comma to force tuple syntax
        if args.strip() == ',':
            args = '()'
        argnames = ll_func.func_code.co_varnames[:nb_args]
        argname2index = dict(zip(argnames, [Index(n) for n in range(nb_args)]))
        self.argtuple = eval(args, argname2index)
        # end of rather XXX'edly hackish parsing

        OOPARGTYPES = []
        arg_llsig_to_oopsig = {}
        for i, obj in enumerate(self.argtuple):
            if isinstance(obj, Index):
                arg_llsig_to_oopsig[obj.n] = i
                OOPARG = FUNCTYPE.ARGS[obj.n]
            else:
                OOPARG = lltype.typeOf(obj)
            OOPARGTYPES.append(OOPARG)

        self.residualargsources = []
        for i in range(nb_args):
            ARGTYPE = FUNCTYPE.ARGS[i]
            if ARGTYPE is not lltype.Void:
                self.residualargsources.append(arg_llsig_to_oopsig[i])

        self.args_gv = [None] * nb_args
        fnptr = fnobj._as_ptr()
        self.gv_fnptr = RGenOp.constPrebuiltGlobal(fnptr)
        result_kind = RGenOp.kindToken(FUNCTYPE.RESULT)
        self.result_kind = result_kind
        if FUNCTYPE.RESULT is lltype.Void:
            self.errorbox = None
            self.gv_whatever_return_value = None
        else:
            error_value = exceptiontransform.error_value(FUNCTYPE.RESULT)
            self.errorbox = rvalue.redbox_from_prebuilt_value(RGenOp,
                                                              error_value)
            self.gv_whatever_return_value = self.errorbox.genvar
        redboxbuilder = rvalue.ll_redboxbuilder(FUNCTYPE.RESULT)
        self.redboxbuilder = redboxbuilder
        self.sigtoken = RGenOp.sigToken(FUNCTYPE)

        if operation_name == 'newlist':
            typename, method = 'list', 'oop_newlist'
            SELFTYPE = FUNCTYPE.RESULT.TO
            is_method = False
        elif operation_name == 'newdict':
            typename, method = 'dict', 'oop_newdict'
            SELFTYPE = FUNCTYPE.RESULT.TO
            is_method = False
        else:
            typename, method = operation_name.split('.')
            method = 'oop_%s_%s' % (typename, method)
            SELFTYPE = FUNCTYPE.ARGS[self.argtuple[0].n].TO
            is_method = True
        self.is_method = is_method

        # hack! to avoid confusion between the .typedesc attribute
        # of oopspecdescs of different types (lists, dicts, etc.)
        # let's use different subclasses for the oopspecdesc too.
        self.__class__ = myrealclass = globals()['OopSpecDesc_%s' % typename]

        vmodule = __import__('pypy.jit.timeshifter.v%s' % (typename,),
                             None, None, [method])
        self.typedesc = vmodule.TypeDesc(RGenOp, rtyper, exceptiondesc,
                                         SELFTYPE)
        handler = getattr(vmodule, method)

        boxargcount_max = handler.func_code.co_argcount - 3
        boxargcount_min = boxargcount_max - len(handler.func_defaults or ())

        def ll_handler(jitstate, oopspecdesc, deepfrozen, *argboxes):
            # an indirection to support the fact that the handler() can
            # take default arguments.  This is an RPython trick to let
            # a family of ll_handler()s be called with a constant number
            # of arguments.  If we tried to call directly the handler()s
            # in a family, the fact that some have extra default arguments
            # and others not causes trouble in normalizecalls.py.
            assert boxargcount_min <= len(argboxes) <= boxargcount_max
            # ^^^ 'assert' is because each call family contains all
            # oopspecs with the rainbow interpreter.  The number of
            # arguments is wrong for many of the oopspecs in the
            # call family, though, so the assert prevents the actual
            # call below from being seen.
            assert isinstance(oopspecdesc, myrealclass)
            if is_method:
                selfbox = argboxes[0]
                assert isinstance(selfbox, rvalue.PtrRedBox)
                return handler(jitstate, oopspecdesc, deepfrozen, selfbox,
                               *argboxes[1:])
            else:
                return handler(jitstate, oopspecdesc, deepfrozen, *argboxes)

        self.ll_handler = ll_handler
        self.couldfold = getattr(handler, 'couldfold', False)

        if self.couldfold:
            oopargcheck = ll_func.oopargcheck    # required if couldfold=True
            # make a copy of the function, for specialization purposes
            oopargcheck = func_with_new_name(oopargcheck,
                                             'argcheck_%s' % (method,))
        else:
            oopargcheck = None

        if True:     # preserve indentation for svn history.
            # This used to be only if couldfold, but it is now
            # always required, for the fallback interp
            ARGS = FUNCTYPE.ARGS
            residualargsources = self.residualargsources
            unrolling_ARGS = unrolling_iterable(ARGS)
            unrolling_OOPARGS = unrolling_iterable(enumerate(OOPARGTYPES))

            def do_call(rgenop, args_gv):
                oopargs = ()
                for i, ARG in unrolling_OOPARGS:
                    v = args_gv[i].revealconst(ARG)
                    oopargs += (v,)
                if oopargcheck is not None:
                    if not oopargcheck(*oopargs):
                        raise SegfaultException
                args = ()
                j = 0
                for ARG in unrolling_ARGS:
                    if ARG == lltype.Void:
                        v = None
                    else:
                        argsrc = residualargsources[j]
                        j = j + 1
                        v = oopargs[argsrc]
                    args += (v,)
                result = maybe_on_top_of_llinterp(exceptiondesc, fnptr)(*args)
                if FUNCTYPE.RESULT == lltype.Void:
                    return None
                return rgenop.genconst(result)

            self.do_call = do_call

    def residual_call(self, jitstate, argboxes, deepfrozen=False):
        builder = jitstate.curbuilder
        args_gv = []
        fold = deepfrozen
        for argsrc in self.residualargsources:
            gv_arg = argboxes[argsrc].getgenvar(jitstate)
            args_gv.append(gv_arg)
            fold &= gv_arg.is_const
        if fold:
            try:
                gv_result = self.do_call(builder.rgenop, args_gv)
            except Exception, e:
                jitstate.residual_exception(e)
                return self.errorbox
        else:
            gv_result = builder.genop_call(self.sigtoken,
                                           self.gv_fnptr, args_gv)
            if self.can_raise:
                jitstate.generated_oop_residual_can_raise = True
        return self.redboxbuilder(self.result_kind, gv_result)

    def residual_exception(self, jitstate, ExcCls):
        from pypy.jit.rainbow.codewriter import residual_exception_nontranslated
        if we_are_translated():
            ll_evalue = get_ll_instance_for_exccls(ExcCls)
            jitstate.residual_ll_exception(ll_evalue)
        else:
            residual_exception_nontranslated(jitstate, ExcCls(), self.rtyper)
        return self.errorbox
    residual_exception._annspecialcase_ = 'specialize:arg(2)'


class OopSpecDesc_list(OopSpecDesc):
    pass

class OopSpecDesc_dict(OopSpecDesc):
    pass


def get_ll_instance_for_exccls(ExcCls):
    raise NotImplementedError

class Entry(ExtRegistryEntry):
    _about_ = get_ll_instance_for_exccls

    def compute_result_annotation(self, s_exccls):
        from pypy.annotation import model as annmodel
        assert s_exccls.is_constant()
        bk = self.bookkeeper
        excdata = bk.annotator.policy.rtyper.exceptiondata
        return annmodel.lltype_to_annotation(excdata.lltype_of_exception_value)

    def specialize_call(self, hop):
        ExcCls = hop.args_s[0].const
        rtyper = hop.rtyper
        bk = rtyper.annotator.bookkeeper
        clsdef = bk.getuniqueclassdef(ExcCls)
        excdata = rtyper.exceptiondata
        ll_evalue = excdata.get_standard_ll_exc_instance(rtyper, clsdef)
        return hop.inputconst(hop.r_result, ll_evalue)

def maybe_on_top_of_llinterp(exceptiondesc, fnptr):
    # Run a generated graph on top of the llinterp for testing.
    # When translated, this just returns the fnptr.
    exc_data_ptr = exceptiondesc.exc_data_ptr
    assert exceptiondesc.rtyper is not None
    llinterp = LLInterpreter(exceptiondesc.rtyper, exc_data_ptr=exc_data_ptr)
    def on_top_of_llinterp(*args):
        return llinterp.eval_graph(get_funcobj(fnptr).graph, list(args))
    return on_top_of_llinterp

class Entry(ExtRegistryEntry):
    _about_ = maybe_on_top_of_llinterp

    def compute_result_annotation(self, s_exceptiondesc, s_fnptr):
        return s_fnptr

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputarg(hop.args_r[1], arg=1)
