from pypy.jit.timeshifter import rvalue, rtimeshift
from pypy.jit.timeshifter.rcontainer import cachedtype, SegfaultException
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.tool.sourcetools import func_with_new_name
from pypy.translator import exceptiontransform
from pypy.translator.simplify import get_funcobj, get_functype
from pypy.jit.rainbow.typesystem import deref

def OopSpecDesc(RGenOp, rtyper, exceptiondesc, opname, oparg, can_raise):
    if opname == 'new':
        cls = NewOopSpecDesc
    elif opname == 'send':
        cls = SendOopSpecDesc
    elif opname == 'call':
        cls = CallOopSpecDesc
    return cls(RGenOp, rtyper, exceptiondesc, oparg, can_raise)

class Index:
    def __init__(self, n):
        self.n = n

class AbstractOopSpecDesc:
    __metaclass__ = cachedtype
    is_method = False

    def __init__(self, RGenOp, rtyper, exceptiondesc, fnobj, can_raise):
        self.rtyper = rtyper
        self.can_raise = can_raise
        self._setup_oopdesc(RGenOp, fnobj)

        if self.RESULT is lltype.Void:
            self.errorbox = None
            self.gv_whatever_return_value = None
        else:
            error_value = exceptiontransform.error_value(self.RESULT)
            self.errorbox = rvalue.redbox_from_prebuilt_value(RGenOp,
                                                              error_value)
            self.gv_whatever_return_value = self.errorbox.genvar
        redboxbuilder = rvalue.ll_redboxbuilder(self.RESULT)
        self.redboxbuilder = redboxbuilder

        # hack! to avoid confusion between the .typedesc attribute
        # of oopspecdescs of different types (lists, dicts, etc.)
        # let's use different subclasses for the oopspecdesc too.
        thisclass = self.__class__.__name__
        self.__class__ = myrealclass = globals()['%s_%s' % (thisclass, self.typename)]

        vmodule = __import__('pypy.jit.timeshifter.v%s' % (self.typename,),
                             None, None, [self.method])
        self.typedesc = vmodule.TypeDesc(RGenOp, rtyper, exceptiondesc,
                                         self.SELFTYPE)
        handler = getattr(vmodule, self.method)

        boxargcount_max = handler.func_code.co_argcount - 3
        boxargcount_min = boxargcount_max - len(handler.func_defaults or ())
        is_method = self.is_method

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
                assert isinstance(selfbox, rvalue.AbstractPtrRedBox)
                return handler(jitstate, oopspecdesc, deepfrozen, selfbox,
                               *argboxes[1:])
            else:
                return handler(jitstate, oopspecdesc, deepfrozen, *argboxes)

        self.ll_handler = ll_handler
        self.couldfold = getattr(handler, 'couldfold', False)

        if self.couldfold:
            # XXX: works only with lltype
            ll_func = fnobj._callable
            oopargcheck = ll_func.oopargcheck    # required if couldfold=True
            # make a copy of the function, for specialization purposes
            oopargcheck = func_with_new_name(oopargcheck,
                                             'argcheck_%s' % (self.method,))
        else:
            oopargcheck = None

        if True:     # preserve indentation for svn history.
            # This used to be only if couldfold, but it is now
            # always required, for the fallback interp
            ARGS = self.ARGS
            residualargsources = self.residualargsources
            unrolling_ARGS = unrolling_iterable(ARGS)
            unrolling_OOPARGS = unrolling_iterable(enumerate(self.OOPARGTYPES))

            RESULT = self.RESULT
            fnptr = self.fnptr
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
                if RESULT == lltype.Void:
                    return None
                return rgenop.genconst(result)

            self.do_call = do_call

    def isfoldable(self, deepfrozen):
        return deepfrozen

    def residual_call(self, jitstate, argboxes, deepfrozen=False):
        builder = jitstate.curbuilder
        args_gv = []
        fold = self.isfoldable(deepfrozen)
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
            gv_result = self.generate_call(builder, args_gv)
            if self.can_raise:
                jitstate.generated_oop_residual_can_raise = True
        return self.redboxbuilder(gv_result)

    def residual_exception(self, jitstate, ExcCls):
        from pypy.jit.rainbow.codewriter import residual_exception_nontranslated
        if we_are_translated():
            ll_evalue = get_ll_instance_for_exccls(ExcCls)
            jitstate.residual_ll_exception(ll_evalue)
        else:
            residual_exception_nontranslated(jitstate, ExcCls(), self.rtyper)
        return self.errorbox
    residual_exception._annspecialcase_ = 'specialize:arg(2)'

    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, self.method)

def parse_oopspec(oopspec, argnames):
    # parse the oopspec and fill in the arguments
    operation_name, args = oopspec.split('(', 1)
    assert args.endswith(')')
    args = args[:-1] + ','     # trailing comma to force tuple syntax
    if args.strip() == ',':
        args = '()'
    nb_args = len(argnames)
    argname2index = dict(zip(argnames, [Index(n) for n in range(nb_args)]))
    argtuple = eval(args, argname2index)
    return operation_name, argtuple

class CallOopSpecDesc(AbstractOopSpecDesc):

    def _setup_oopdesc(self, RGenOp, fnobj):
        FUNCTYPE = lltype.typeOf(fnobj)
        self.ARGS = FUNCTYPE.ARGS
        self.RESULT = FUNCTYPE.RESULT
        ll_func = fnobj._callable
        nb_args = len(FUNCTYPE.ARGS)

        argnames = ll_func.func_code.co_varnames[:nb_args]
        operation_name, argtuple = parse_oopspec(ll_func.oopspec, argnames)
        self.argtuple = argtuple

        self.OOPARGTYPES = []
        arg_llsig_to_oopsig = {}
        for i, obj in enumerate(self.argtuple):
            if isinstance(obj, Index):
                arg_llsig_to_oopsig[obj.n] = i
                OOPARG = FUNCTYPE.ARGS[obj.n]
            else:
                OOPARG = lltype.typeOf(obj)
            self.OOPARGTYPES.append(OOPARG)

        self.residualargsources = []
        for i in range(nb_args):
            ARGTYPE = FUNCTYPE.ARGS[i]
            if ARGTYPE is not lltype.Void:
                self.residualargsources.append(arg_llsig_to_oopsig[i])

        if operation_name == 'newlist':
            self.typename = 'list'
            self.method = 'oop_newlist'
            self.SELFTYPE = deref(FUNCTYPE.RESULT)
            self.is_method = False
        elif operation_name == 'newdict':
            self.typename = 'dict'
            self.method = 'oop_newdict'
            self.SELFTYPE = deref(FUNCTYPE.RESULT)
            is_method = False
        else:
            self.typename, method = operation_name.split('.')
            self.method = 'oop_%s_%s' % (self.typename, method)
            self.SELFTYPE = deref(FUNCTYPE.ARGS[self.argtuple[0].n])
            self.is_method = True

        self.fnptr = fnobj._as_ptr()
        self.gv_fnptr = RGenOp.constPrebuiltGlobal(self.fnptr)
        self.sigtoken = RGenOp.sigToken(FUNCTYPE)

        # the following attributes seem to be unused
##        result_kind = RGenOp.kindToken(FUNCTYPE.RESULT)
##        self.result_kind = result_kind
##        self.args_gv = [None] * nb_args

    def generate_call(self, builder, args_gv):
        return builder.genop_call(self.sigtoken, self.gv_fnptr, args_gv)


class CallOopSpecDesc_list(CallOopSpecDesc):
    pass

class CallOopSpecDesc_dict(CallOopSpecDesc):
    pass


class NewOopSpecDesc(AbstractOopSpecDesc):
    def _setup_oopdesc(self, RGenOp, TYPE):
        self.SELFTYPE = TYPE
        self.RESULT = TYPE
        self.typename = TYPE.oopspec_name
        self.method = 'oop_new%s' % self.typename
        self.is_method = False
        opname, argtuple = parse_oopspec(TYPE.oopspec_new,
                                         TYPE.oopspec_new_argnames)
        assert opname == 'new'
        self.argtuple = argtuple

        if isinstance(TYPE, ootype.Array):
            def allocate(length):
                return ootype.oonewarray(TYPE, length)
            self.ARGS = [ootype.Signed]
            self.OOPARGTYPES = [ootype.Signed]
            self.residualargsources = [0]
            self.fnptr = self.rtyper.annotate_helper_fn(allocate,
                                                        [ootype.Signed])
        else:
            self.ARGS = []
            self.OOPARGTYPES = []
            self.residualargsources = []
            def allocate():
                return ootype.new(TYPE)
            self.fnptr = self.rtyper.annotate_helper_fn(allocate, [])

class NewOopSpecDesc_list(NewOopSpecDesc):
    pass

class NewOopSpecDesc_dict(NewOopSpecDesc):
    pass


class SendOopSpecDesc(AbstractOopSpecDesc):
    def _setup_oopdesc(self, RGenOp, meth):
        METH = ootype.typeOf(meth)
        assert METH.SELFTYPE is not None, 'fix ootype'
        self.SELFTYPE = METH.SELFTYPE
        self.ARGS = [METH.SELFTYPE] + list(METH.ARGS)
        self.RESULT = METH.RESULT

        wrapper = ootype.build_unbound_method_wrapper(meth)
        self.fnptr = self.rtyper.annotate_helper_fn(wrapper, self.ARGS)

        # we assume the number and position of the arguments are the
        # same as in the original oosend
        self.OOPARGTYPES = [self.SELFTYPE] + list(METH.ARGS)
        self.residualargsources = range(len(self.OOPARGTYPES))
        self.typename = self.SELFTYPE.oopspec_name
        methname = meth._name.lstrip('_')
        assert methname.startswith('ll_')
        methname = methname[3:]
        self.method = 'oop_%s_method_%s' % (self.typename, methname)
        self.is_method = True
        self.methtoken = RGenOp.methToken(self.SELFTYPE, meth._name)
        
        self.foldable = False
        if isinstance(self.SELFTYPE, ootype.Array):
            if self.SELFTYPE._hints.get('immutable', False):
                self.foldable = True
        if getattr(meth, '_callable', None) and \
           getattr(meth._callable, 'foldable', False):
            self.foldable = True

    def generate_call(self, builder, args_gv):
        gv_self, args_gv = args_gv[0], args_gv[1:]
        return builder.genop_oosend(self.methtoken, gv_self, args_gv)

    def isfoldable(self, deepfrozen):
        return deepfrozen or self.foldable

class SendOopSpecDesc_list(SendOopSpecDesc):
    pass

class SendOopSpecDesc_dict(SendOopSpecDesc):
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
    funcobj = get_funcobj(fnptr)
    if hasattr(funcobj, 'graph'):
        def on_top_of_llinterp(*args):
            return llinterp.eval_graph(funcobj.graph, list(args))
    else:
        assert isinstance(fnptr, ootype._meth)
        assert hasattr(fnptr, '_callable')
        def on_top_of_llinterp(*args):
            return fnptr._callable(*args)
    return on_top_of_llinterp

class Entry(ExtRegistryEntry):
    _about_ = maybe_on_top_of_llinterp

    def compute_result_annotation(self, s_exceptiondesc, s_fnptr):
        return s_fnptr

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputarg(hop.args_r[1], arg=1)
