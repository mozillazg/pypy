from functools import partial

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.lltype import Void
from pypy.translator.oosupport.function import Function as OOFunction
from pypy.translator.avm.node import Node
from pypy.translator.avm.avm1gen import ClassName

def load_variable_hook(self, v):
    if v.name in self.argset:
        selftype, selfname = self.args[0]
        if self.is_method and v.name == selfname:
            self.generator.push_this() # special case for 'self'
        else:
            self.generator.push_arg(v)
        return True
    return False
    

class Function(OOFunction, Node):
    
    auto_propagate_exceptions = True

    def __init__(self, *args, **kwargs):
        OOFunction.__init__(self, *args, **kwargs)
        
        if hasattr(self.db.genoo, 'exceptiontransformer'):
            self.auto_propagate_exceptions = False
        
        namespace = getattr(self.graph.func, '_namespace_', None)
        if namespace:
            if '.' in namespace:
                self.namespace, self.classname = namespace.rsplit('.', 1)
            else:
                self.namespace = None
                self.classname = namespace
        else:
            self.namespace = None
            self.classname = None

    def _create_generator(self, ilasm):
        ilasm.db = self.db
        ilasm.load_variable_hook = partial(load_variable_hook, self)
        return ilasm
    
    def record_ll_meta_exc(self, ll_meta_exc):
        # record the type only if it doesn't belong to a native_class
        ll_exc = ll_meta_exc._INSTANCE
        NATIVE_INSTANCE = ll_exc._hints.get('NATIVE_INSTANCE', None)
        if NATIVE_INSTANCE is None:
            OOFunction.record_ll_meta_exc(self, ll_meta_exc)

    def begin_render(self):
        self._set_args()
        self._set_locals()
        if self.args:
            args = zip(*self.args)[1]
        else:
            args = ()
        if self.is_method:
            self.generator.begin_method(self.name, ClassName(self.namespace, self.classname), args[1:])
        elif self.classname:
            self.generator.begin_static_method(self.name, ClassName(self.namespace, self.classname), args)
        else:
            self.generator.begin_function(self.name, args)
        
    def end_render(self):
        if self.generator.scope.islabel:
            self.generator.exit_scope()
        self.generator.exit_scope()
        
    def render_return_block(self, block):
        print "RETURN BLOCK RENDERING"
        return_var = block.inputargs[0]
        if return_var.concretetype is not Void:
            self.generator.load(return_var)
        self.generator.return_stmt()

    def set_label(self, label):
        return self.generator.set_label(label)

    # def _render_op(self, op):
    #     #instr_list = self.db.genoo.opcodes.get(op.opname, None)
    #     #instr_list.render(self.generator, op)
    #    super(Function, self)._render_op(op)

    def _setup_link(self, link):
        target = link.target
        linkvars = []
        for to_load, to_store in zip(link.args, target.inputargs):
            if isinstance(to_load, flowmodel.Variable) and to_load.name == to_store.name:
                continue
            if to_load.concretetype is ootype.Void:
                continue
            linkvars.append((to_load, to_store))

        # after SSI_to_SSA it can happen to have to_load = [a, b] and
        # to_store = [b, c].  If we store each variable sequentially,
        # 'b' would be overwritten before being read.  To solve, we
        # first load all the values on the stack, then store in the
        # appropriate places.

        if self._trace_enabled():
            self._trace('link', writeline=True)
            for to_load, to_store in linkvars:
                self._trace_value('%s <-- %s' % (to_store, to_load), to_load)
            self._trace('', writeline=True)
        
        for to_load, to_store in linkvars:
            self.generator.load(to_store)
            self.generator.load(to_load)
            self.generator.set_variable()

    
    # def begin_try(self, cond):
    #     if cond:
    #         self.ilasm.begin_try()
    
    # def end_try(self, target_label, cond):
    #     if cond:
    #         self.ilasm.leave(target_label)
    #         self.ilasm.end_try()
    #     else:
    #         self.ilasm.branch(target_label)

    # def begin_catch(self, llexitcase):
    #     ll_meta_exc = llexitcase
    #     ll_exc = ll_meta_exc._INSTANCE
    #     cts_exc = self.cts.lltype_to_cts(ll_exc)
    #     self.ilasm.begin_catch(cts_exc.classname())

    # def end_catch(self, target_label):
    #     self.ilasm.leave(target_label)
    #     self.ilasm.end_catch()

    # def render_raise_block(self, block):
    #     exc = block.inputargs[1]
    #     self.load(exc)
    #     self.ilasm.opcode('throw')

    # def store_exception_and_link(self, link):
    #     if self._is_raise_block(link.target):
    #         # the exception value is on the stack, use it as the 2nd target arg
    #         assert len(link.args) == 2
    #         assert len(link.target.inputargs) == 2
    #         self.store(link.target.inputargs[1])
    #     else:
    #         # the exception value is on the stack, store it in the proper place
    #         if isinstance(link.last_exception, flowmodel.Variable):
    #             self.ilasm.opcode('dup')
    #             self.store(link.last_exc_value)
    #             self.ilasm.call_method(
    #                 'class [mscorlib]System.Type object::GetType()',
    #                 virtual=True)
    #             self.store(link.last_exception)
    #         else:
    #             self.store(link.last_exc_value)
    #         self._setup_link(link)

    # def render_numeric_switch(self, block):
    #     if block.exitswitch.concretetype in (ootype.SignedLongLong, ootype.UnsignedLongLong):
    #         # TODO: it could be faster to check is the values fit in
    #         # 32bit, and perform a cast in that case
    #         self.render_numeric_switch_naive(block)
    #         return

    #     cases, min_case, max_case, default = self._collect_switch_cases(block)
    #     is_sparse = self._is_sparse_switch(cases, min_case, max_case)

    #     naive = (min_case < 0) or is_sparse
    #     if naive:
    #         self.render_numeric_switch_naive(block)
    #         return

    #     targets = []
    #     for i in xrange(max_case+1):
    #         link, lbl = cases.get(i, default)
    #         targets.append(lbl)
    #     self.generator.load(block.exitswitch)
    #     self.ilasm.switch(targets)
    #     self.render_switch_case(*default)
    #     for link, lbl in cases.itervalues():
    #         self.render_switch_case(link, lbl)

    # def call_oostring(self, ARGTYPE):
    #     if isinstance(ARGTYPE, ootype.Instance):
    #         argtype = self.cts.types.object
    #     else:
    #         argtype = self.cts.lltype_to_cts(ARGTYPE)
    #     self.call_signature('string [pypylib]pypy.runtime.Utils::OOString(%s, int32)' % argtype)

    # def call_oounicode(self, ARGTYPE):
    #     argtype = self.cts.lltype_to_cts(ARGTYPE)
    #     self.call_signature('string [pypylib]pypy.runtime.Utils::OOUnicode(%s)' % argtype)

    # Those parts of the generator interface that are function
    # specific
