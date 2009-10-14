from pypy.translator.simplify import get_funcobj
from pypy.jit.metainterp import support, history
from pypy.rpython.lltypesystem import lltype, rclass
from pypy.tool.udir import udir

class JitPolicy(object):
    def __init__(self):
        self.unsafe_loopy_graphs = set()

    def dump_unsafe_loops(self):
        f = udir.join("unsafe-loops.txt").open('w')
        strs = [str(graph) for graph in self.unsafe_loopy_graphs]
        strs.sort()
        for graph in strs:
            print >> f, graph
        f.close()

    portal_runner_ptr = None # set by WarmRunnerDesc.rewrite_jit_merge_point

    def look_inside_function(self, func):
        if hasattr(func, '_jit_look_inside_'):
            return func._jit_look_inside_
        # explicitly pure functions are always opaque
        if getattr(func, '_pure_function_', False):
            return False
        # pypy.rpython.module.* are opaque helpers
        mod = func.__module__ or '?'
        if mod.startswith('pypy.rpython.module.'):
            return False
        return True

    def look_inside_graph(self, graph, supports_floats):
        from pypy.translator.backendopt.support import find_backedges
        contains_loop = bool(find_backedges(graph))
        unsupported = contains_unsupported_variable_type(graph,
                                                         supports_floats)
        try:
            func = graph.func
        except AttributeError:
            see_function = True
        else:
            see_function = self.look_inside_function(func)
            contains_loop = contains_loop and not getattr(
                    func, '_jit_unroll_safe_', False)

        res = see_function and not unsupported
        if res and contains_loop:
            self.unsafe_loopy_graphs.add(graph)
        return res and not contains_loop

    def graphs_from(self, op, rtyper, supports_floats):
        if op.opname == 'direct_call':
            funcobj = get_funcobj(op.args[0].value)
            graph = funcobj.graph
            if self.look_inside_graph(graph, supports_floats):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname in ('indirect_call', 'oosend')
            if op.opname == 'indirect_call':
                graphs = op.args[-1].value
            else:
                v_obj = op.args[1].concretetype
                graphs = v_obj._lookup_graphs(op.args[0].value)
            if graphs is not None:
                result = []
                for graph in graphs:
                    if self.look_inside_graph(graph, supports_floats):
                        result.append(graph)
                if result:
                    return result  # common case: look inside these graphs,
                                   # and ignore the others if there are any
            else:
                # special case: handle the indirect call that goes to
                # the 'instantiate' methods.  This check is a bit imprecise
                # but it's not too bad if we mistake a random indirect call
                # for the one to 'instantiate'.
                CALLTYPE = op.args[0].concretetype
                if (op.opname == 'indirect_call' and len(op.args) == 2 and
                    CALLTYPE == rclass.OBJECT_VTABLE.instantiate):
                    return list(self._graphs_of_all_instantiate(rtyper))
        # residual call case: we don't need to look into any graph
        return None

    def _graphs_of_all_instantiate(self, rtyper):
        for vtable in rtyper.lltype2vtable.values():
            if vtable.instantiate:
                yield vtable.instantiate._obj.graph

    def guess_call_kind(self, op, rtyper, supports_floats):
        if op.opname == 'direct_call':
            funcptr = op.args[0].value
            funcobj = get_funcobj(funcptr)
            if funcptr is self.portal_runner_ptr:
                return 'recursive'
            if getattr(funcobj, 'graph', None) is None:
                return 'residual'
            targetgraph = funcobj.graph
            if (hasattr(targetgraph, 'func') and
                hasattr(targetgraph.func, 'oopspec')):
                return 'builtin'
        elif op.opname == 'oosend':
            SELFTYPE, methname, opargs = support.decompose_oosend(op)
            if SELFTYPE.oopspec_name is not None:
                return 'builtin'
        if self.graphs_from(op, rtyper, supports_floats) is None:
            return 'residual'
        return 'regular'

def contains_unsupported_variable_type(graph, supports_floats):
    getkind = history.getkind
    try:
        for block in graph.iterblocks():
            for v in block.inputargs:
                getkind(v.concretetype, supports_floats)
            for op in block.operations:
                for v in op.args:
                    getkind(v.concretetype, supports_floats)
                getkind(op.result.concretetype, supports_floats)
    except NotImplementedError, e:
        history.log.WARNING('%s, ignoring graph' % (e,))
        history.log.WARNING('  %s' % (graph,))
        return True
    return False

# ____________________________________________________________

class StopAtXPolicy(JitPolicy):
    def __init__(self, *funcs):
        JitPolicy.__init__(self)
        self.funcs = funcs

    def look_inside_function(self, func):
        if func in self.funcs:
            return False
        return super(StopAtXPolicy, self).look_inside_function(func)
