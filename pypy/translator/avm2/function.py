
from itertools import chain

from py.builtin import set

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.lltype import Void
from pypy.translator.oosupport.function import Function as OOFunction

from pypy.translator.avm2.node import Node
from mech.fusion.avm2 import constants

class CompiledABCNode(Node):
    def __init__(self, abc):
        self.abc = abc

    def render(self, ilasm):
        ilasm.abc.merge(self.abc)

class Function(OOFunction, Node):
    auto_propagate_exceptions = True
    def __init__(self, db, graph, name=None, is_method=False, is_entrypoint=False):
        OOFunction.__init__(self, db, graph, name, is_method, is_entrypoint)

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

        self.override = False

    def _create_generator(self, ilasm):
        ilasm.db = self.db
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
        if not self.args:
            self.args = ()

        if self.is_method:
            self.args = self.args[1:]

        returntype, returnvar = self.cts.llvar_to_cts(self.graph.getreturnvar())

        if self.classname:
            self.generator.begin_class(constants.packagedQName(self.namespace, self.classname))

        self.generator.begin_method(self.name, self.args, returntype, static=not self.is_method, override=self.override)

        # self.declare_locals()

    def end_render(self):
        self.generator.end_method()
        if self.classname:
            self.generator.end_class()

    def render_return_block(self, block):
        return_var = block.inputargs[0]
        if return_var.concretetype is Void:
            self.generator.emit('returnvoid')
        else:
            self.generator.load(return_var)
            self.generator.emit('returnvalue')

    def set_label(self, label):
        return self.generator.set_label(label)

    def get_block_locals(self, block, exits=False):
        if not block.operations:
            return set()
        all_locals  = set(arg.name for op in block.operations for arg in op.args if isinstance(arg, flowmodel.Variable))
        all_locals |= set(op.result.name for op in block.operations)
        all_locals -= set(arg.name for arg in self.graph.getargs() if isinstance(arg, flowmodel.Variable))
        if exits:
            all_locals -= set(arg.name for exit in block.exits
                              for arg in exit.args + exit.target.inputargs
                              if isinstance(arg, flowmodel.Variable))
        if isinstance(block.exitswitch, flowmodel.Variable) and block.exitswitch.name in all_locals:
            all_locals.remove(block.exitswitch.name)
        return all_locals

    def get_block_links_args(self, link):
        return set(arg.name for exit in link.prevblock.exits for arg in exit.args if arg not in link.args if isinstance(arg, flowmodel.Variable))

    def end_block(self, block):
        L = self.get_block_locals(block, True)
        for var in self.get_block_locals(block, True):
            if self.generator.HL(var):
                self.generator.KL(var)

    def __eq__(self, other):
        return type(self) == type(other) and self.graph == other.graph

    ## def declare_locals(self):
    ##     for TYPE, name in set(self.locals):
    ##         TYPE.load_default(self.generator)
    ##         self.generator.store_var(name)

    def _trace_enabled(self):
        return False

    def _trace(self, s, writeline=False):
        print "TRACE:", s

    def _trace_value(self, prompt, v):
        print "TRACE: P:", prompt, "V:", v

    def _render_op(self, op):
        print "Rendering op:", op
        super(Function, self)._render_op(op)

    def _setup_link(self, link):
        target = link.target
        linkvars = []
        locals = self.get_block_locals(link.prevblock) | self.get_block_links_args(link)
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
            self.generator.load(to_load)
            if isinstance(to_load, flowmodel.Variable) and to_load.name in locals:
                self.generator.KL(to_load.name)

        for to_load, to_store in reversed(linkvars):
            self.generator.store(to_store)

    def begin_try(self, cond):
        if cond:
            self.ilasm.begin_try()

    def end_try(self, target_label, cond):
        if cond:
            self.ilasm.end_try()
        self.ilasm.branch_unconditionally(target_label)

    def begin_catch(self, llexitcase):
        ll_meta_exc = llexitcase
        ll_exc = ll_meta_exc._INSTANCE
        self.ilasm.begin_catch(self.cts.instance_to_qname(ll_exc))

    def end_catch(self, target_label):
        self.ilasm.end_catch()
        self.ilasm.branch_unconditionally(target_label)

    def render_raise_block(self, block):
        exc = block.inputargs[1]
        self.generator.load(exc)
        self.generator.emit('throw')

    def store_exception_and_link(self, link):
        if self._is_raise_block(link.target):
            # the exception value is on the stack, use it as the 2nd target arg
            assert len(link.args) == 2
            assert len(link.target.inputargs) == 2
            self.generator.store(link.target.inputargs[1])
        else:
            # the exception value is on the stack, store it in the proper place
            if isinstance(link.last_exception, flowmodel.Variable):
                self.generator.emit('dup')
                self.generator.store(link.last_exc_value)
                self.generator.emit('convert_o')
                self.generator.get_field('prototype')
                self.generator.get_field('constructor')
                self.generator.store(link.last_exception)
            else:
                self.generator.store(link.last_exc_value)
            self._setup_link(link)

    def render_normal_block(self, block):
        for op in block.operations:
            self._render_op(op)

        self.end_block(block)

        if block.exitswitch is None:
            assert len(block.exits) == 1
            link = block.exits[0]
            target_label = self._get_block_name(link.target)
            self._setup_link(link)
            self.generator.branch_unconditionally(target_label)
        elif block.exitswitch.concretetype is ootype.Bool:
            self.render_bool_switch(block)
        elif block.exitswitch.concretetype in (ootype.Signed, ootype.SignedLongLong,
                                               ootype.Unsigned, ootype.UnsignedLongLong,
                                               ootype.Char, ootype.UniChar):
            self.render_numeric_switch(block)
        else:
            assert False, 'Unknonw exitswitch type: %s' % block.exitswitch.concretetype

    def render_bool_switch(self, block):
        assert len(block.exits) == 2
        for link in block.exits:
            if link.exitcase:
                link_true = link
            else:
                link_false = link

        true_label = self.next_label('link_true')
        self.generator.load(block.exitswitch)
        self.generator.KL(block.exitswitch.name, True)
        self.generator.branch_conditionally(True, true_label)
        self._follow_link(link_false) # if here, the exitswitch is false
        self.set_label(true_label)
        self._follow_link(link_true)  # if here, the exitswitch is true

    def _follow_link(self, link):
        target_label = self._get_block_name(link.target)
        allowed = self.get_block_locals(link.prevblock) | self.get_block_links_args(link)
        for arg in chain(*(exit.args for exit in link.prevblock.exits)):
            if isinstance(arg, flowmodel.Variable) and arg.name in allowed and arg not in link.args and self.generator.HL(arg.name):
                self.generator.KL(arg.name)
        self._setup_link(link)
        self.generator.branch_unconditionally(target_label)


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

    # Those parts of the generator interface that are function
    # specific
