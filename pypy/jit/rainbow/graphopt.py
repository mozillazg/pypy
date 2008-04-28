from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype


def _getoopspec(op):
    if op.opname == 'direct_call':
        fnobj = op.args[0].value._obj
        if hasattr(fnobj._callable, 'oopspec'):
            oopspec = fnobj._callable.oopspec
            if '(' in oopspec:
                return oopspec[:oopspec.index('(')]
    return ''

def is_vable_setter(op):
    return _getoopspec(op).startswith('vable.set_')

def is_vable_getter(op):
    return _getoopspec(op).startswith('vable.get_')

def vable_fieldname(op):
    oopspec = _getoopspec(op)
    assert oopspec.startswith('vable.get_') or oopspec.startswith('vable.set_')
    return oopspec[len('vable.get_'):]

def is_vableptr(TYPE):
    return (isinstance(TYPE, lltype.Ptr) and
            isinstance(TYPE.TO, lltype.Struct) and
            TYPE.TO._hints.get('virtualizable'))


class VirtualizableAccessTracker(object):
    """Tracks which accesses to fields of virtualizable structures
    are safe to replace with direct getfield or setfield.
    """

    def __init__(self, residual_call_targets):
        self.residual_call_targets = residual_call_targets
        self.safe_variables = set()
        # set of graphs left to analyze:
        self.pending_graphs = set()
        # for each graph with virtualizable input args, if we have seen
        # at least one call to it, we record in 'graph2safeargs[graph]' the
        # set of input args that are safe through all possible calls
        self.graph2safeargs = {}
        # for all operations that are setters or getters: True if safe
        self.safe_operations = {}

    def find_safe_points(self, graphlist):
        for graph in graphlist:
            for block in graph.iterblocks():
                for op in block.operations:
                    if op.opname == 'malloc':
                        self.add_safe_variable(graph, op.result)
                    elif (op.opname == 'jit_marker' and
                          op.args[0].value == 'jit_merge_point'):
                        for v in op.args[2:]:
                            self.add_safe_variable(graph, v)

    def add_safe_variable(self, graph, v):
        if is_vableptr(v.concretetype):
            self.safe_variables.add(v)
            self.pending_graphs.add(graph)

    def seeing_call(self, graph, safe_args):
        if graph in self.residual_call_targets:
            return      # don't follow that call
        prevset = self.graph2safeargs.get(graph)
        if prevset is None:
            self.graph2safeargs[graph] = set(safe_args)
        else:
            self.graph2safeargs[graph] &= set(safe_args)
        if self.graph2safeargs[graph] != prevset:
            self.pending_graphs.add(graph)

    def follow_call(self, args, graph, is_unsafe):
        safe_args = None
        assert len(args) == len(graph.getargs())
        for v1, v2 in zip(args, graph.getargs()):
            if is_vableptr(v2.concretetype):
                if safe_args is None:
                    safe_args = []
                if not is_unsafe(v1):
                    safe_args.append(v2)
        if safe_args is not None:
            self.seeing_call(graph, safe_args)

    def track_in_graph(self, graph):
        # inside a graph, we propagate 'unsafety': we start from all
        # operations that produce a virtualizable pointer and that are
        # not explicitly marked as safe, and propagate forward.
        unsafe = set(graph.getargs())
        if graph in self.graph2safeargs:
            unsafe -= self.graph2safeargs[graph]

        def is_unsafe(v):
            return (isinstance(v, Constant) or
                    (v in unsafe and v not in self.safe_variables))

        pending_blocks = set(graph.iterblocks())
        while pending_blocks:
            block = pending_blocks.pop()
            for op in block.operations:
                if op.opname == 'cast_pointer':
                    if is_unsafe(op.args[0]):
                        unsafe.add(op.result)
                else:
                    unsafe.add(op.result)
            for link in block.exits:
                for v1, v2 in zip(link.args, link.target.inputargs):
                    if is_unsafe(v1) and v2 not in unsafe:
                        unsafe.add(v2)
                        pending_blocks.add(link.target)

        # done following, now find and record all calls
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'direct_call':
                    if is_vable_setter(op) or is_vable_getter(op):
                        v = op.args[1]
                        self.safe_operations[op] = not is_unsafe(v)
                    elif hasattr(op.args[0].value._obj, 'graph'):
                        callargs = op.args[1:]
                        calltarget = op.args[0].value._obj.graph
                        self.follow_call(callargs, calltarget, is_unsafe)
                elif op.opname == 'indirect_call':
                    callargs = op.args[1:-1]
                    calltargets = op.args[-1].value
                    if calltargets is not None:
                        for calltarget in calltargets:
                            self.follow_call(callargs, calltarget, is_unsafe)

    def propagate(self):
        while self.pending_graphs:
            graph = self.pending_graphs.pop()
            self.track_in_graph(graph)

    def replace_safe_operations(self):
        for op, safe in self.safe_operations.items():
            if safe:
                name = vable_fieldname(op)
                c_name = Constant(name, lltype.Void)
                if is_vable_setter(op):
                    c_setterfn, v_ptr, v_value = op.args
                    op.opname = 'setfield'
                    op.args = [v_ptr, c_name, v_value]
                elif is_vable_getter(op):
                    c_getterfn, v_ptr = op.args
                    op.opname = 'getfield'
                    op.args = [v_ptr, c_name]
                else:
                    assert 0


def simplify_virtualizable_accesses(codewriter):
    assert codewriter.hannotator.policy.hotpath, (
        "too many potential residual calls in the non-hotpath policy")
    tracker = VirtualizableAccessTracker(codewriter.residual_call_targets)
    tracker.find_safe_points(codewriter.rtyper.annotator.translator.graphs)
    tracker.propagate()
    tracker.replace_safe_operations()
