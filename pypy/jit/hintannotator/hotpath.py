from pypy.objspace.flow.model import checkgraph, copygraph, Constant
from pypy.objspace.flow.model import Block, Link, SpaceOperation, Variable
from pypy.translator.unsimplify import split_block, varoftype
from pypy.translator.simplify import join_blocks
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags
from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import inputconst
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.jit import JitHintError


class HotPathHintAnnotator(HintAnnotator):

    def build_hotpath_types(self):
        self.jitdriverclasses = {}
        self.prepare_portal_graphs()
        graph = self.portalgraph_with_on_enter_jit
        input_args_hs = [SomeLLAbstractConstant(v.concretetype,
                                                {OriginFlags(): True})
                         for v in graph.getargs()]
        return self.build_types(graph, input_args_hs)

    def prepare_portal_graphs(self):
        # find the graph with the jit_merge_point()
        found_at = []
        for graph in self.base_translator.graphs:
            place = find_jit_merge_point(graph)
            if place is not None:
                found_at.append(place)
        if len(found_at) != 1:
            raise JitHintError("found %d graphs with a jit_merge_point(),"
                               " expected 1 (for now)" % len(found_at))
        origportalgraph, _, origportalop = found_at[0]
        drivercls = origportalop.args[0].value
        self.jitdriverclasses[drivercls] = True
        #
        # We make a copy of origportalgraph and mutate it to make it
        # the portal.  The portal really starts at the jit_merge_point()
        # without any block or operation before it.
        #
        portalgraph = copygraph(origportalgraph)
        block = split_before_jit_merge_point(None, portalgraph)
        assert block is not None
        # rewire the graph to start at the global_merge_point
        portalgraph.startblock.isstartblock = False
        portalgraph.startblock = block
        portalgraph.startblock.isstartblock = True
        self.portalgraph = portalgraph
        self.origportalgraph = origportalgraph
        # check the new graph: errors mean some live vars have not
        # been listed in the jit_merge_point()
        # (XXX should give an explicit JitHintError explaining the problem)
        checkgraph(portalgraph)
        # insert the on_enter_jit() logic before the jit_merge_point()
        # in a copy of the graph which will be the one that gets hint-annotated
        # and turned into rainbow bytecode.  On the other hand, the
        # 'self.portalgraph' is the copy that will run directly, in
        # non-JITting mode, so it should not contain the on_enter_jit() call.
        if hasattr(drivercls, 'on_enter_jit'):
            anothercopy = copygraph(portalgraph)
            anothercopy.tag = 'portal'
            insert_on_enter_jit_handling(self.base_translator.rtyper,
                                         anothercopy,
                                         drivercls)
            self.portalgraph_with_on_enter_jit = anothercopy
        else:
            self.portalgraph_with_on_enter_jit = portalgraph  # same is ok
        # put the new graph back in the base_translator
        portalgraph.tag = 'portal'
        self.base_translator.graphs.append(portalgraph)

# ____________________________________________________________

def find_jit_merge_point(graph):
    found_at = []
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'jit_merge_point':
                found_at.append((graph, block, op))
    if len(found_at) > 1:
        raise JitHintError("multiple jit_merge_point() not supported")
    if found_at:
        return found_at[0]
    else:
        return None

def split_before_jit_merge_point(hannotator, graph):
    """Find the block with 'jit_merge_point' and split just before,
    making sure the input args are in the canonical order.  If
    hannotator is not None, preserve the hint-annotations while doing so
    (used by codewriter.py).
    """
    found_at = find_jit_merge_point(graph)
    if found_at is not None:
        _, portalblock, portalop = found_at
        portalopindex = portalblock.operations.index(portalop)
        # split the block just before the jit_merge_point()
        if portalopindex > 0:
            link = split_block(hannotator, portalblock, portalopindex)
            portalblock = link.target
            portalop = portalblock.operations[0]
        # split again, this time enforcing the order of the live vars
        # specified by the user in the jit_merge_point() call
        assert portalop.opname == 'jit_merge_point'
        livevars = [v for v in portalop.args[1:]
                      if v.concretetype is not lltype.Void]
        link = split_block(hannotator, portalblock, 0, livevars)
        return link.target
    else:
        return None

def insert_on_enter_jit_handling(rtyper, graph, drivercls):
    vars = [varoftype(v.concretetype, name=v) for v in graph.getargs()]
    newblock = Block(vars)

    op = graph.startblock.operations[0]
    assert op.opname == 'jit_merge_point'
    assert op.args[0].value is drivercls
    allvars = []
    i = 0
    for v in op.args[1:]:
        if v.concretetype is lltype.Void:
            allvars.append(Constant(None, concretetype=lltype.Void))
        else:
            allvars.append(vars[i])
            i += 1
    assert i == len(vars)

    llops = LowLevelOpList(rtyper)
    # generate ops to make an instance of DriverCls
    classdef = rtyper.annotator.bookkeeper.getuniqueclassdef(drivercls)
    s_instance = annmodel.SomeInstance(classdef)
    r_instance = rtyper.getrepr(s_instance)
    v_self = r_instance.new_instance(llops)
    # generate ops to store the 'greens' and 'reds' variables on 'self'
    num_greens = len(drivercls.greens)
    num_reds = len(drivercls.reds)
    assert len(allvars) == num_greens + num_reds
    for name, v_value in zip(drivercls.reds, allvars[num_greens:]):
        r_instance.setfield(v_self, name, v_value, llops)
    # generate a call to on_enter_jit(self, invariants, *greens)
    on_enter_jit_func = drivercls.on_enter_jit.im_func
    s_func = rtyper.annotator.bookkeeper.immutablevalue(on_enter_jit_func)
    r_func = rtyper.getrepr(s_func)
    c_func = r_func.get_unique_llfn()
    v_invariants = inputconst(lltype.Void, None)
    vlist = allvars[:num_greens]
    llops.genop('direct_call', [c_func, v_self, v_invariants] + vlist)
    # generate ops to reload the 'reds' variables from 'self'
    # XXX Warning!  the 'greens' variables are not reloaded.  This is
    # a bit of a mess color-wise, and probably not useful.
    newvars = allvars[:num_greens]
    for name, v_value in zip(drivercls.reds, allvars[num_greens:]):
        v_value = r_instance.getfield(v_self, name, llops)
        newvars.append(v_value)
    newvars = [v for v in newvars if v.concretetype is not lltype.Void]
    # done, fill the block and link it to make it the startblock
    newblock.operations[:] = llops
    newblock.closeblock(Link(newvars, graph.startblock))
    graph.startblock.isstartblock = False
    graph.startblock = newblock
    graph.startblock.isstartblock = True
    checkgraph(graph)
