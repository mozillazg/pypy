from pypy.objspace.flow.model import SpaceOperation, Constant, Variable
from pypy.rpython.lltypesystem import lltype
from pypy.translator.unsimplify import varoftype
from pypy.rlib import jit
from pypy.jit.codewriter.call import CallControl
from pypy.jit.codewriter import support
from pypy.jit.codewriter.policy import JitPolicy


def test_graphs_from_direct_call():
    cc = CallControl()
    F = lltype.FuncType([], lltype.Signed)
    f = lltype.functionptr(F, 'f', graph='fgraph')
    v = varoftype(lltype.Signed)
    op = SpaceOperation('direct_call', [Constant(f, lltype.Ptr(F))], v)
    #
    lst = cc.graphs_from(op, {}.__contains__)
    assert lst is None     # residual call
    #
    lst = cc.graphs_from(op, {'fgraph': True}.__contains__)
    assert lst == ['fgraph']     # normal call

def test_graphs_from_indirect_call():
    cc = CallControl()
    F = lltype.FuncType([], lltype.Signed)
    v = varoftype(lltype.Signed)
    graphlst = ['f1graph', 'f2graph']
    op = SpaceOperation('indirect_call', [varoftype(lltype.Ptr(F)),
                                          Constant(graphlst, lltype.Void)], v)
    #
    lst = cc.graphs_from(op, {'f1graph': True, 'f2graph': True}.__contains__)
    assert lst == ['f1graph', 'f2graph']     # normal indirect call
    #
    lst = cc.graphs_from(op, {'f1graph': True}.__contains__)
    assert lst == ['f1graph']     # indirect call, look only inside some graphs
    #
    lst = cc.graphs_from(op, {}.__contains__)
    assert lst is None            # indirect call, don't look inside any graph

def test_graphs_from_no_target():
    cc = CallControl()
    F = lltype.FuncType([], lltype.Signed)
    v = varoftype(lltype.Signed)
    op = SpaceOperation('indirect_call', [varoftype(lltype.Ptr(F)),
                                          Constant(None, lltype.Void)], v)
    lst = cc.graphs_from(op, {}.__contains__)
    assert lst is None

# ____________________________________________________________

def test_find_all_graphs():
    def f(x):
        if x < 0:
            return f(-x)
        return x + 1
    @jit.purefunction
    def g(x):
        return x + 2
    @jit.dont_look_inside
    def h(x):
        return x + 3
    def i(x):
        return f(x) * g(x) * h(x)

    rtyper = support.annotate(i, [7])
    cc = CallControl()
    jitpolicy = JitPolicy()
    res = cc.find_all_graphs(rtyper.annotator.translator.graphs[0],
                             jitpolicy)
    translator = rtyper.annotator.translator

    funcs = set([graph.func for graph in res])
    assert funcs == set([i, f])

def test_find_all_graphs_without_floats():
    def g(x):
        return int(x * 12.5)
    def f(x):
        return g(x) + 1
    rtyper = support.annotate(f, [7])
    cc = CallControl()
    jitpolicy = JitPolicy()
    jitpolicy.set_supports_floats(True)
    translator = rtyper.annotator.translator
    res = cc.find_all_graphs(translator.graphs[0], jitpolicy)
    funcs = set([graph.func for graph in res])
    assert funcs == set([f, g])

    cc = CallControl()
    jitpolicy.set_supports_floats(False)
    res = cc.find_all_graphs(translator.graphs[0], jitpolicy)
    funcs = [graph.func for graph in res]
    assert funcs == [f]

def test_find_all_graphs_loops():
    def g(x):
        i = 0
        while i < x:
            i += 1
        return i
    @jit.unroll_safe
    def h(x):
        i = 0
        while i < x:
            i += 1
        return i

    def f(x):
        i = 0
        while i < x*x:
            i += g(x) + h(x)
        return i

    rtyper = support.annotate(f, [7])
    cc = CallControl()
    jitpolicy = JitPolicy()
    translator = rtyper.annotator.translator
    res = cc.find_all_graphs(translator.graphs[0], jitpolicy)
    funcs = set([graph.func for graph in res])
    assert funcs == set([f, h])

def test_unroll_safe_and_inline():
    @jit.unroll_safe
    def h(x):
        i = 0
        while i < x:
            i += 1
        return i
    h._always_inline_ = True

    def g(x):
        return h(x)

    rtyper = support.annotate(g, [7])
    cc = CallControl()
    jitpolicy = JitPolicy()
    translator = rtyper.annotator.translator
    res = cc.find_all_graphs(translator.graphs[0], jitpolicy)
    funcs = set([graph.func for graph in res])
    assert funcs == set([g, h])

def test_find_all_graphs_str_join():
    def i(x, y):
        return "hello".join([str(x), str(y), "bye"])

    rtyper = support.annotate(i, [7, 100])
    cc = CallControl()
    jitpolicy = JitPolicy()
    translator = rtyper.annotator.translator
    # does not explode
    cc.find_all_graphs(translator.graphs[0], jitpolicy)

# ____________________________________________________________

def test_guess_call_kind_and_calls_from_graphs():
    class portal_runner_obj:
        graph = object()
    g = object()
    g1 = object()
    cc = CallControl(portal_runner_obj=portal_runner_obj)
    cc.candidate_graphs = [g, g1]

    op = SpaceOperation('direct_call', [Constant(portal_runner_obj)],
                        Variable())
    assert cc.guess_call_kind(op) == 'recursive'

    op = SpaceOperation('direct_call', [Constant(object())],
                        Variable())
    assert cc.guess_call_kind(op) == 'residual'        

    class funcptr:
        class graph:
            class func:
                oopspec = "spec"
    op = SpaceOperation('direct_call', [Constant(funcptr)],
                        Variable())
    assert cc.guess_call_kind(op) == 'builtin'

    class funcptr:
        graph = g
    op = SpaceOperation('direct_call', [Constant(funcptr)],
                        Variable())
    res = cc.graphs_from(op)
    assert res == [g]        
    assert cc.guess_call_kind(op) == 'regular'

    class funcptr:
        graph = object()
    op = SpaceOperation('direct_call', [Constant(funcptr)],
                        Variable())
    res = cc.graphs_from(op)
    assert res is None        
    assert cc.guess_call_kind(op) == 'residual'

    h = object()
    op = SpaceOperation('indirect_call', [Variable(),
                                          Constant([g, g1, h])],
                        Variable())
    res = cc.graphs_from(op)
    assert res == [g, g1]
    assert cc.guess_call_kind(op) == 'regular'

    op = SpaceOperation('indirect_call', [Variable(),
                                          Constant([h])],
                        Variable())
    res = cc.graphs_from(op)
    assert res is None
    assert cc.guess_call_kind(op) == 'residual'        
