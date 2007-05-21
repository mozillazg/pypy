from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy
from pypy.lang.prolog.interpreter import term, engine
from pypy.translator.translator import graphof
from pypy.annotation.specialize import getuniquenondirectgraph


forbidden_modules = {'pypy.lang.prolog.interpreter.parser': True,
                     }

good_modules = {'pypy.lang.prolog.builtin.control': True,
                'pypy.lang.prolog.builtin.register': True
               }

PORTAL = engine.Engine.portal_try_rule.im_func

class PyrologHintAnnotatorPolicy(HintAnnotatorPolicy):
    novirtualcontainer = True
    oopspec = True

    def seetranslator(self, t):
        portal = getattr(PORTAL, 'im_func', PORTAL)
        portal_graph = graphof(t, portal)
        self.timeshift_graphs = timeshift_graphs(t, portal_graph)

    def look_inside_graph(self, graph):
        if graph in self.timeshift_graphs:
            return self.timeshift_graphs[graph]
        try:
            func = graph.func
        except AttributeError:
            return True
        if hasattr(func, '_look_inside_me_'):
            return func._look_inside_me_
        mod = func.__module__ or '?'
        if mod in forbidden_modules:
            return False
        if mod in good_modules:
            return True
        if mod.startswith("pypy.lang.prolog"):
            return False
        return True

def jitme(func):
    func._look_inside_me_ = True
    return func

def dontjitme(func):
    func._look_inside_me_ = False
    return func


def enumerate_reachable_graphs(translator, startgraph):
    from pypy.translator.backendopt.support import find_calls_from
    pending = [(startgraph, None)]
    yield pending[0]
    seen = {startgraph: True}
    while pending:
        yield None     # hack: a separator meaning "length increases now"
        nextlengthlist = []
        nextseen = {}
        for node in pending:
            head, tail = node
            for block, callee in find_calls_from(translator, head):
                if callee not in seen:
                    newnode = callee, node
                    yield newnode
                    nextlengthlist.append(newnode)
                    nextseen[callee] = True
        pending = nextlengthlist
        seen.update(nextseen)
    yield None

def graphs_on_the_path_to(translator, startgraph, targetgraphs):
    targetgraphs = targetgraphs.copy()
    result = {}
    found = {}
    for node in enumerate_reachable_graphs(translator, startgraph):
        if node is None:  # hack: a separator meaning "length increases now"
            for graph in found:
                del targetgraphs[graph]
            found.clear()
            if not targetgraphs:
                return result
        elif node[0] in targetgraphs:
            found[node[0]] = True
            while node is not None:
                head, tail = node
                result[head] = True
                node = tail
    raise Exception("did not reach all targets:\nmissing %r" % (
        targetgraphs.keys(),))


def timeshift_graphs(t, portal_graph):
    import pypy
    result_graphs = {}

    bk = t.annotator.bookkeeper

    def _graph(func):
        func = getattr(func, 'im_func', func)
        desc = bk.getdesc(func)
        return getuniquenondirectgraph(desc)

    def seefunc(fromfunc, *tofuncs):
        targetgraphs = {}
        for tofunc in tofuncs:
            targetgraphs[_graph(tofunc)] = True
        graphs = graphs_on_the_path_to(t, _graph(fromfunc), targetgraphs)
        for graph in graphs:
            result_graphs[graph] = True

    def seepath(*path):
        for i in range(1, len(path)):
            seefunc(path[i-1], path[i])

    def seegraph(func, look=True):
        graph = _graph(func)
        if look:
            extra = ""
            if look != True:
                extra = " substituted with %s" % look
        result_graphs[graph] = look

    for cls in [term.Var, term.Term, term.Number, term.Float, term.Atom]:
        seegraph(cls.copy)
        seegraph(cls.__init__)
        seegraph(cls.copy_and_unify)
    for cls in [term.Term, term.Number, term.Atom]:
        seegraph(cls.copy_and_basic_unify)
        seegraph(cls.dereference)
        seegraph(cls.copy_and_basic_unify)
    for cls in [term.Var, term.Term, term.Number, term.Atom]:
        seegraph(cls.get_unify_hash)
    for cls in [term.Callable, term.Atom, term.Term]:
        seegraph(cls.get_prolog_signature)
    seegraph(PORTAL)
    seegraph(pypy.lang.prolog.interpreter.engine.Heap.newvar)
    seegraph(pypy.lang.prolog.interpreter.term.Rule.clone_and_unify_head)
    seegraph(pypy.lang.prolog.interpreter.engine.Engine.call)
    seegraph(pypy.lang.prolog.interpreter.engine.Engine._call)
    seegraph(pypy.lang.prolog.interpreter.engine.Engine.user_call)
    seegraph(pypy.lang.prolog.interpreter.engine.Engine._user_call)
    seegraph(pypy.lang.prolog.interpreter.engine.Engine.try_rule)
    seegraph(pypy.lang.prolog.interpreter.engine.Engine._try_rule)
    seegraph(pypy.lang.prolog.interpreter.engine.Engine.main_loop)
    seegraph(pypy.lang.prolog.interpreter.engine.LinkedRules.find_applicable_rule)
    seegraph(pypy.lang.prolog.interpreter.engine.Continuation.call)
    seegraph(term.Term.unify_hash_of_child)
    for cls in [engine.Continuation, engine.LimitedScopeContinuation,
                pypy.lang.prolog.builtin.control.AndContinuation]:
        seegraph(cls._call)
    return result_graphs

def get_portal(drv):
    t = drv.translator
    portal = getattr(PORTAL, 'im_func', PORTAL)

    policy = PyrologHintAnnotatorPolicy()
    policy.seetranslator(t)
    return portal, policy
