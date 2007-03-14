import types
from pypy.module.pypyjit.interp_jit import PORTAL

from pypy.objspace.flow.model import checkgraph
from pypy.translator.translator import graphof
from pypy.jit.hintannotator.annotator import HintAnnotator, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import OriginFlags, SomeLLAbstractConstant

PORTAL = getattr(PORTAL, 'im_func', PORTAL)


class PyPyHintAnnotatorPolicy(HintAnnotatorPolicy):

    def __init__(self, timeshift_graphs):
        HintAnnotatorPolicy.__init__(self, novirtualcontainer = True,
                                           oopspec = True)
        self.timeshift_graphs = timeshift_graphs

    def look_inside_graph(self, graph):
        if graph in self.timeshift_graphs:
            return True
        try:
            func = graph.func
        except AttributeError:
            return True
        mod = func.__module__ or '?'
        if mod.startswith('pypy.objspace'):
            return False
        if mod.startswith('pypy.module.'):
            if not mod.startswith('pypy.module.pypyjit.'):
                return False
        if mod in forbidden_modules:
            return False
        return True

forbidden_modules = {'pypy.interpreter.gateway': True,
                     #'pypy.interpreter.baseobjspace': True,
                     'pypy.interpreter.typedef': True,
                     'pypy.interpreter.eval': True,
                     'pypy.interpreter.function': True,
                     'pypy.interpreter.pytraceback': True,
                     }

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
    result_graphs = {}

    def _graph(func):
        func = getattr(func, 'im_func', func)
        return graphof(t, func)

    def seefunc(fromfunc, *tofuncs):
        targetgraphs = {}
        for tofunc in tofuncs:
            targetgraphs[_graph(tofunc)] = True
        graphs = graphs_on_the_path_to(t, _graph(fromfunc), targetgraphs)
        result_graphs.update(graphs)

    def seepath(*path):
        for i in range(1, len(path)):
            seefunc(path[i-1], path[i])

    # --------------------
    import pypy
    seepath(pypy.interpreter.pyframe.PyFrame.BINARY_ADD,
            pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.intobject.add__Int_Int,
            pypy.objspace.std.inttype.wrapint,
            pypy.objspace.std.intobject.W_IntObject.__init__)
    seepath(pypy.objspace.descroperation._invoke_binop,
            pypy.objspace.descroperation._check_notimplemented)
    seepath(pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.Space.type)
    #seepath(pypy.objspace.descroperation.DescrOperation.xxx,
    #        pypy.objspace.std.typeobject.W_TypeObject.lookup,
    #        pypy.objspace.std.typeobject.W_TypeObject.getdictvalue_w)
    seepath(pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.typeobject.W_TypeObject.lookup_where,
            pypy.objspace.std.typeobject.W_TypeObject.getdictvalue_w)
    # --------------------

    return result_graphs


def hintannotate(drv):
    t = drv.translator
    portal_graph = graphof(t, PORTAL)

    POLICY = PyPyHintAnnotatorPolicy(timeshift_graphs(t, portal_graph))

    graphnames = [str(_g) for _g in POLICY.timeshift_graphs]
    graphnames.sort()
    print '-' * 20
    for graphname in graphnames:
        print graphname
    print '-' * 20
    import pdb; pdb.set_trace()

    hannotator = HintAnnotator(base_translator=t, policy=POLICY)
    hs = hannotator.build_types(portal_graph,
                                [SomeLLAbstractConstant(v.concretetype,
                                                        {OriginFlags(): True})
                                 for v in portal_graph.getargs()])
    drv.log.info('Hint-annotated %d graphs.' % (
        len(hannotator.translator.graphs),))
    n = len(list(hannotator.translator.graphs[0].iterblocks()))
    drv.log.info("portal has %d blocks" % n)
    drv.hannotator = hannotator
    #import pdb; pdb.set_trace()

def timeshift(drv):
    from pypy.jit.timeshifter.hrtyper import HintRTyper
    #from pypy.jit.codegen.llgraph.rgenop import RGenOp
    from pypy.jit.codegen.i386.rgenop import RI386GenOp as RGenOp
    RGenOp.MC_SIZE = 32 * 1024 * 1024     # 32MB - but supposed infinite!

    ha = drv.hannotator
    t = drv.translator
    # make the timeshifted graphs
    hrtyper = HintRTyper(ha, t.rtyper, RGenOp)
    origportalgraph = graphof(t, PORTAL)
    hrtyper.specialize(origportalgraph=origportalgraph, view=False)
        
    # XXX temp
    drv.source()
