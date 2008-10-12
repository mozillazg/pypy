from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph, copygraph
from pypy.objspace.flow.model import c_last_exception
from pypy.translator.backendopt.support import log
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype


# ____________________________________________________________


class MallocTypeDesc(object):

    def __init__(self, MALLOCTYPE):
        if not isinstance(MALLOCTYPE, lltype.GcStruct):
            raise CannotRemoveThisType
        self.MALLOCTYPE = MALLOCTYPE
        self.check_no_destructor()
        self.names_and_types = []
        self.name2index = {}
        self.initialize_type(MALLOCTYPE)
        #self.immutable_struct = MALLOCTYPE._hints.get('immutable')

    def check_no_destructor(self):
        STRUCT = self.MALLOCTYPE
        try:
            rttiptr = lltype.getRuntimeTypeInfo(STRUCT)
        except ValueError:
            return    # ok
        destr_ptr = getattr(rttiptr._obj, 'destructor_funcptr', None)
        if destr_ptr:
            raise CannotRemoveThisType

    def initialize_type(self, TYPE):
        fieldnames = TYPE._names
        firstname, FIRSTTYPE = TYPE._first_struct()
        if FIRSTTYPE is not None:
            self.initialize_type(FIRSTTYPE)
            fieldnames = fieldnames[1:]
        for name in fieldnames:
            FIELDTYPE = TYPE._flds[name]
            self.name2index[name] = len(self.names_and_types)
            self.names_and_types.append((name, FIELDTYPE))


class SpecNode(object):
    pass


class RuntimeSpecNode(SpecNode):

    def __init__(self, name, TYPE):
        self.name = name
        self.TYPE = TYPE

    def newvar(self):
        v = Variable(self.name)
        v.concretetype = self.TYPE
        return v

    def getfrozenkey(self, memo):
        return 'R'

    def accumulate_nodes(self, rtnodes, vtnodes):
        rtnodes.append(self)

    def copy(self, memo, flagreadonly):
        return RuntimeSpecNode(self.name, self.TYPE)


class VirtualSpecNode(SpecNode):

    def __init__(self, typedesc, fields, readonly=False):
        self.typedesc = typedesc
        self.fields = fields     # list of SpecNodes
        self.readonly = readonly

    def getfrozenkey(self, memo):
        if self in memo:
            return memo[self]
        else:
            memo[self] = len(memo)
            result = [self.typedesc, self.readonly]
            for subnode in self.fields:
                result.append(subnode.getfrozenkey(memo))
            return tuple(result)

    def accumulate_nodes(self, rtnodes, vtnodes):
        if self in vtnodes:
            return
        vtnodes[self] = True
        for subnode in self.fields:
            subnode.accumulate_nodes(rtnodes, vtnodes)

    def copy(self, memo, flagreadonly):
        if self in memo:
            return memo[self]
        readonly = self.readonly or self in flagreadonly
        newnode = VirtualSpecNode(self.typedesc, [], readonly)
        memo[self] = newnode
        for subnode in self.fields:
            newnode.fields.append(subnode.copy(memo, flagreadonly))
        return newnode


class VirtualFrame(object):

    def __init__(self, sourcegraph, sourceblock, nextopindex,
                 allnodes, callerframe=None):
        self.varlist = vars_alive_through_op(sourceblock, nextopindex)
        self.nodelist = [allnodes[v] for v in self.varlist]
        self.sourcegraph = sourcegraph
        self.sourceblock = sourceblock
        self.nextopindex = nextopindex
        self.callerframe = callerframe

    def get_nodes_in_use(self):
        return dict(zip(self.varlist, self.nodelist))

    def copy(self, memo, flagreadonly={}):
        newframe = VirtualFrame.__new__(VirtualFrame)
        newframe.varlist = self.varlist
        newframe.nodelist = [node.copy(memo, flagreadonly)
                             for node in self.nodelist]
        newframe.sourcegraph = self.sourcegraph
        newframe.sourceblock = self.sourceblock
        newframe.nextopindex = self.nextopindex
        if self.callerframe is None:
            newframe.callerframe = None
        else:
            newframe.callerframe = self.callerframe.copy(memo, flagreadonly)
        return newframe

    def enum_call_stack(self):
        frame = self
        while frame is not None:
            yield frame
            frame = frame.callerframe

    def getfrozenkey(self):
        memo = {}
        key = []
        for frame in self.enum_call_stack():
            key.append(frame.sourceblock)
            key.append(frame.nextopindex)
            for node in frame.nodelist:
                key.append(node.getfrozenkey(memo))
        return tuple(key)

    def find_all_nodes(self):
        rtnodes = []
        vtnodes = {}
        for frame in self.enum_call_stack():
            for node in frame.nodelist:
                node.accumulate_nodes(rtnodes, vtnodes)
        return rtnodes, vtnodes

    def find_rt_nodes(self):
        rtnodes, vtnodes = self.find_all_nodes()
        return rtnodes

    def find_vt_nodes(self):
        rtnodes, vtnodes = self.find_all_nodes()
        return vtnodes

    def return_to_caller(self, retnode):
        callerframe = self.callerframe
        if callerframe is None:
            raise ForcedInline("return block")
        for i in range(len(callerframe.nodelist)):
            if isinstance(callerframe.nodelist[i], FutureReturnValue):
                callerframe.nodelist[i] = retnode
        return callerframe

    def handle_raise(self, linkargsnodes):
        if not is_trivial_nodelist(linkargsnodes):
            raise CannotVirtualize("except block")
            # ^^^ this could also be a ForcedInline, to try to match the
            # exception raising and catching globally.  But it looks
            # overkill for now.

        # XXX this assumes no exception handler in the callerframes
        topframe = self
        while topframe.callerframe is not None:
            topframe = topframe.callerframe
        targetblock = topframe.sourcegraph.exceptblock
        self.fixup_except_block(targetblock)
        return topframe, targetblock

    def fixup_except_block(self, block):
        # hack: this block's inputargs may be missing concretetypes...
        e1, v1 = block.inputargs
        e2, v2 = self.sourcegraph.exceptblock.inputargs
        e1.concretetype = e2.concretetype
        v1.concretetype = v2.concretetype


def copynodes(nodelist, flagreadonly={}):
    memo = {}
    return [node.copy(memo, flagreadonly) for node in nodelist]

def find_all_nodes(nodelist):
    rtnodes = []
    vtnodes = {}
    for node in nodelist:
        node.accumulate_nodes(rtnodes, vtnodes)
    return rtnodes, vtnodes

def is_trivial_nodelist(nodelist):
    for node in nodelist:
        if not isinstance(node, RuntimeSpecNode):
            return False
    return True


class CannotVirtualize(Exception):
    pass

class ForcedInline(Exception):
    pass

class CannotRemoveThisType(Exception):
    pass


class MallocVirtualizer(object):

    def __init__(self, graphs, verbose=False):
        self.graphs = graphs
        self.graphbuilders = {}
        self.specialized_graphs = {}
        self.inline_and_remove = {}    # {graph: op_to_remove}
        self.inline_and_remove_seen = {}   # set of (graph, op_to_remove)
        self.malloctypedescs = {}
        self.count_virtualized = 0
        self.verbose = verbose

    def report_result(self):
        log.mallocv('removed %d mallocs so far' % (self.count_virtualized,))
        return self.count_virtualized

    def enum_all_mallocs(self, graph):
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'malloc':
                    MALLOCTYPE = op.result.concretetype.TO
                    try:
                        self.getmalloctypedesc(MALLOCTYPE)
                    except CannotRemoveThisType:
                        pass
                    else:
                        yield (block, op)
                elif op.opname == 'direct_call':
                    fobj = op.args[0].value._obj
                    graph = getattr(fobj, 'graph', None)
                    if graph in self.inline_and_remove:
                        yield (block, op)

    def remove_mallocs_once(self):
        self.flush_failed_specializations()
        prev = self.count_virtualized
        count_inline_and_remove = len(self.inline_and_remove)
        for graph in self.graphs:
            seen = {}
            while True:
                for block, op in self.enum_all_mallocs(graph):
                    if op.result not in seen:
                        seen[op.result] = True
                        if self.try_remove_malloc(graph, block, op):
                            break   # graph mutated, restart enum_all_mallocs()
                else:
                    break   # enum_all_mallocs() exhausted, graph finished
        progress1 = self.report_result() - prev
        progress2 = len(self.inline_and_remove) - count_inline_and_remove
        return progress1 or bool(progress2)

    def flush_failed_specializations(self):
        for key, (mode, specgraph) in self.specialized_graphs.items():
            if mode == 'fail':
                del self.specialized_graphs[key]

    def getmalloctypedesc(self, MALLOCTYPE):
        try:
            dsc = self.malloctypedescs[MALLOCTYPE]
        except KeyError:
            dsc = self.malloctypedescs[MALLOCTYPE] = MallocTypeDesc(MALLOCTYPE)
        return dsc

    def try_remove_malloc(self, graph, block, op):
        if (graph, op) in self.inline_and_remove_seen:
            return False      # no point in trying again
        graphbuilder = GraphBuilder(self, graph)
        if graph in self.graphbuilders:
            graphbuilder.initialize_from_old_builder(self.graphbuilders[graph])
        graphbuilder.start_from_a_malloc(graph, block, op.result)
        try:
            graphbuilder.propagate_specializations()
        except CannotVirtualize, e:
            self.logresult(op, 'failed', e)
            return False
        except ForcedInline, e:
            self.logresult(op, 'forces inlining', e)
            self.inline_and_remove[graph] = op
            self.inline_and_remove_seen[graph, op] = True
            return False
        else:
            self.logresult(op, 'removed')
            graphbuilder.finished_removing_malloc()
            self.graphbuilders[graph] = graphbuilder
            self.count_virtualized += 1
            return True

    def logresult(self, op, msg, exc=None):    # only for nice log outputs
        if self.verbose:
            if exc is None:
                exc = ''
            else:
                exc = ': %s' % (exc,)
            chain = []
            while True:
                chain.append(str(op.result))
                if op.opname != 'direct_call':
                    break
                fobj = op.args[0].value._obj
                op = self.inline_and_remove[fobj.graph]
            log.mallocv('%s %s%s' % ('->'.join(chain), msg, exc))

    def get_specialized_graph(self, graph, nodelist):
        assert len(graph.getargs()) == len(nodelist)
        if is_trivial_nodelist(nodelist):
            return 'trivial', graph
        nodes = dict(zip(graph.getargs(), nodelist))
        virtualframe = VirtualFrame(graph, graph.startblock, 0, nodes)
        key = virtualframe.getfrozenkey()
        try:
            return self.specialized_graphs[key]
        except KeyError:
            self.build_specialized_graph(graph, key, nodelist)
            return self.specialized_graphs[key]

    def build_specialized_graph(self, graph, key, nodelist):
        graph2 = copygraph(graph)
        nodes = dict(zip(graph2.getargs(), nodelist))
        virtualframe = VirtualFrame(graph2, graph2.startblock, 0, nodes)
        graphbuilder = GraphBuilder(self, graph2)
        specblock = graphbuilder.start_from_virtualframe(virtualframe)
        specblock.isstartblock = True
        specgraph = graph2
        specgraph.name += '_mallocv'
        specgraph.startblock = specblock
        self.specialized_graphs[key] = ('call', specgraph)
        try:
            graphbuilder.propagate_specializations()
        except ForcedInline, e:
            if self.verbose:
                log.mallocv('%s inlined: %s' % (graph.name, e))
            self.specialized_graphs[key] = ('inline', None)
        except CannotVirtualize, e:
            if self.verbose:
                log.mallocv('%s failing: %s' % (graph.name, e))
            self.specialized_graphs[key] = ('fail', None)
        else:
            self.graphbuilders[specgraph] = graphbuilder
            self.graphs.append(specgraph)


class GraphBuilder(object):

    def __init__(self, mallocv, graph):
        self.mallocv = mallocv
        self.graph = graph
        self.specialized_blocks = {}
        self.pending_specializations = []

    def initialize_from_old_builder(self, oldbuilder):
        self.specialized_blocks.update(oldbuilder.specialized_blocks)

    def start_from_virtualframe(self, startframe):
        spec = BlockSpecializer(self)
        spec.initialize_renamings(startframe)
        self.pending_specializations.append(spec)
        return spec.specblock

    def start_from_a_malloc(self, graph, block, v_result):
        assert v_result in [op.result for op in block.operations]
        nodes = {}
        for v in block.inputargs:
            nodes[v] = RuntimeSpecNode(v, v.concretetype)
        trivialframe = VirtualFrame(graph, block, 0, nodes)
        spec = BlockSpecializer(self, v_result)
        spec.initialize_renamings(trivialframe)
        self.pending_specializations.append(spec)
        self.pending_patch = (block, spec.specblock)

    def finished_removing_malloc(self):
        (srcblock, specblock) = self.pending_patch
        srcblock.inputargs = specblock.inputargs
        srcblock.operations = specblock.operations
        srcblock.exitswitch = specblock.exitswitch
        srcblock.recloseblock(*specblock.exits)

    def get_specialized_block(self, virtualframe, v_expand_malloc=None):
        key = virtualframe.getfrozenkey()
        specblock = self.specialized_blocks.get(key)
        if specblock is None:
            orgblock = virtualframe.sourceblock
            assert len(orgblock.exits) != 0
            spec = BlockSpecializer(self, v_expand_malloc)
            spec.initialize_renamings(virtualframe)
            self.pending_specializations.append(spec)
            specblock = spec.specblock
            self.specialized_blocks[key] = specblock
        return specblock

    def propagate_specializations(self):
        while self.pending_specializations:
            spec = self.pending_specializations.pop()
            spec.specialize_operations()
            spec.follow_exits()


class BlockSpecializer(object):

    def __init__(self, graphbuilder, v_expand_malloc=None):
        self.graphbuilder = graphbuilder
        self.v_expand_malloc = v_expand_malloc
        self.specblock = Block([])

    def initialize_renamings(self, virtualframe):
        # we make a copy of the original 'virtualframe' because the
        # specialize_operations() will mutate some of its content.
        virtualframe = virtualframe.copy({})
        self.virtualframe = virtualframe
        self.nodes = virtualframe.get_nodes_in_use()
        self.renamings = {}    # {RuntimeSpecNode(): Variable()}
        specinputargs = []
        for rtnode in virtualframe.find_rt_nodes():
            v = rtnode.newvar()
            self.renamings[rtnode] = v
            specinputargs.append(v)
        self.specblock.inputargs = specinputargs

    def setnode(self, v, node):
        assert v not in self.nodes
        self.nodes[v] = node

    def getnode(self, v):
        if isinstance(v, Variable):
            return self.nodes[v]
        else:
            rtnode = RuntimeSpecNode('const', v.concretetype)
            self.renamings[rtnode] = v
            return rtnode

    def rename_nonvirtual(self, v, where=None):
        if not isinstance(v, Variable):
            return v
        node = self.nodes[v]
        if not isinstance(node, RuntimeSpecNode):
            raise CannotVirtualize(where)
        return self.renamings[node]

    def expand_nodes(self, nodelist):
        rtnodes, vtnodes = find_all_nodes(nodelist)
        return [self.renamings[rtnode] for rtnode in rtnodes]

    def specialize_operations(self):
        newoperations = []
        # note that 'self.virtualframe' can be changed during the loop!
        while True:
            operations = self.virtualframe.sourceblock.operations
            try:
                op = operations[self.virtualframe.nextopindex]
                self.virtualframe.nextopindex += 1
            except IndexError:
                break

            meth = getattr(self, 'handle_op_' + op.opname,
                           self.handle_default)
            newoperations += meth(op)
        self.specblock.operations = newoperations

    def follow_exits(self):
        block = self.virtualframe.sourceblock
        self.specblock.exitswitch = self.rename_nonvirtual(block.exitswitch,
                                                           'exitswitch')
        catch_exc = self.specblock.exitswitch == c_last_exception
        newlinks = []
        for link in block.exits:
            is_exc_link = catch_exc and link.exitcase is not None
            if is_exc_link:
                extravars = []
                for attr in ['last_exception', 'last_exc_value']:
                    v = getattr(link, attr)
                    if isinstance(v, Variable):
                        rtnode = RuntimeSpecNode(v, v.concretetype)
                        self.setnode(v, rtnode)
                        self.renamings[rtnode] = v = rtnode.newvar()
                    extravars.append(v)

            currentframe = self.virtualframe
            linkargsnodes = [self.getnode(v1) for v1 in link.args]
            targetblock = link.target

            if is_except(targetblock):
                currentframe, targetblock = currentframe.handle_raise(
                    linkargsnodes)

            assert len(targetblock.inputargs) == len(linkargsnodes)
            targetnodes = dict(zip(targetblock.inputargs, linkargsnodes))

            if (currentframe.callerframe is None and
                  is_trivial_nodelist(linkargsnodes)):
                # there is no more VirtualSpecNodes being passed around,
                # so we can stop specializing
                rtnodes = linkargsnodes
                specblock = targetblock
            else:
                if is_return(targetblock):
                    newframe = currentframe.return_to_caller(linkargsnodes[0])
                    v_expand_malloc = None
                else:
                    newframe = VirtualFrame(currentframe.sourcegraph,
                                            targetblock, 0, targetnodes,
                                          callerframe=currentframe.callerframe)
                    v_expand_malloc = self.v_expand_malloc
                rtnodes = newframe.find_rt_nodes()
                specblock = self.graphbuilder.get_specialized_block(newframe,
                                                               v_expand_malloc)

            linkargs = [self.renamings[rtnode] for rtnode in rtnodes]
            newlink = Link(linkargs, specblock)
            newlink.exitcase = link.exitcase
            if hasattr(link, 'llexitcase'):
                newlink.llexitcase = link.llexitcase
            if is_exc_link:
                newlink.extravars(*extravars)
            newlinks.append(newlink)
        self.specblock.closeblock(*newlinks)

    def make_rt_result(self, v_result):
        newrtnode = RuntimeSpecNode(v_result, v_result.concretetype)
        self.setnode(v_result, newrtnode)
        v_new = newrtnode.newvar()
        self.renamings[newrtnode] = v_new
        return v_new

    def handle_default(self, op):
        newargs = [self.rename_nonvirtual(v, op) for v in op.args]
        newresult = self.make_rt_result(op.result)
        return [SpaceOperation(op.opname, newargs, newresult)]

    def handle_unreachable(self, op):
        from pypy.rpython.lltypesystem.rstr import string_repr
        msg = 'unreachable: %s' % (op,)
        ll_msg = string_repr.convert_const(msg)
        c_msg = Constant(ll_msg, lltype.typeOf(ll_msg))
        newresult = self.make_rt_result(op.result)
        return [SpaceOperation('debug_fatalerror', [c_msg], newresult)]

    def handle_op_getfield(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            fieldname = op.args[1].value
            index = node.typedesc.name2index[fieldname]
            self.setnode(op.result, node.fields[index])
            return []
        else:
            return self.handle_default(op)

    def handle_op_setfield(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            if node.readonly:
                raise ForcedInline(op)
            fieldname = op.args[1].value
            index = node.typedesc.name2index[fieldname]
            node.fields[index] = self.getnode(op.args[2])
            return []
        else:
            return self.handle_default(op)

    def handle_op_same_as(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            node = self.getnode(op.args[0])
            self.setnode(op.result, node)
            return []
        else:
            return self.handle_default(op)

    def handle_op_cast_pointer(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            node = self.getnode(op.args[0])
            SOURCEPTR = lltype.Ptr(node.typedesc.MALLOCTYPE)
            TARGETPTR = op.result.concretetype
            try:
                if lltype.castable(TARGETPTR, SOURCEPTR) < 0:
                    raise lltype.InvalidCast
            except lltype.InvalidCast:
                return self.handle_unreachable(op)
            self.setnode(op.result, node)
            return []
        else:
            return self.handle_default(op)

    def handle_op_keepalive(self, op):
        node = self.getnode(op.args[0])
        if isinstance(node, VirtualSpecNode):
            return []
        else:
            return self.handle_default(op)

    def handle_op_malloc(self, op):
        if op.result is self.v_expand_malloc:
            MALLOCTYPE = op.result.concretetype.TO
            typedesc = self.graphbuilder.mallocv.getmalloctypedesc(MALLOCTYPE)
            virtualnode = VirtualSpecNode(typedesc, [])
            self.setnode(op.result, virtualnode)
            for name, FIELDTYPE in typedesc.names_and_types:
                fieldnode = RuntimeSpecNode(name, FIELDTYPE)
                virtualnode.fields.append(fieldnode)
                c = Constant(FIELDTYPE._defl())
                c.concretetype = FIELDTYPE
                self.renamings[fieldnode] = c
            self.v_expand_malloc = None      # done
            return []
        else:
            return self.handle_default(op)

    def handle_op_direct_call(self, op):
        fobj = op.args[0].value._obj
        if not hasattr(fobj, 'graph'):
            return self.handle_default(op)
        graph = fobj.graph
        nb_args = len(op.args) - 1
        assert nb_args == len(graph.getargs())
        newnodes = [self.getnode(v) for v in op.args[1:]]
        myframe = self.get_updated_frame(op)
        mallocv = self.graphbuilder.mallocv

        if op.result is self.v_expand_malloc:
            # move to inlining the callee, and continue looking for the
            # malloc to expand in the callee's graph
            op_to_remove = mallocv.inline_and_remove[graph]
            self.v_expand_malloc = op_to_remove.result
            return self.handle_inlined_call(myframe, graph, newnodes)

        argnodes = copynodes(newnodes, flagreadonly=myframe.find_vt_nodes())
        kind, newgraph = mallocv.get_specialized_graph(graph, argnodes)
        if kind == 'trivial':
            return self.handle_default(op)
        elif kind == 'inline':
            return self.handle_inlined_call(myframe, graph, newnodes)
        elif kind == 'call':
            return self.handle_residual_call(op, newgraph, newnodes)
        elif kind == 'fail':
            raise CannotVirtualize(op)
        else:
            raise ValueError(kind)

    def get_updated_frame(self, op):
        sourcegraph = self.virtualframe.sourcegraph
        sourceblock = self.virtualframe.sourceblock
        nextopindex = self.virtualframe.nextopindex
        self.nodes[op.result] = FutureReturnValue(op)
        myframe = VirtualFrame(sourcegraph, sourceblock, nextopindex,
                               self.nodes,
                               self.virtualframe.callerframe)
        del self.nodes[op.result]
        return myframe

    def handle_residual_call(self, op, newgraph, newnodes):
        fspecptr = getfunctionptr(newgraph)
        newargs = [Constant(fspecptr,
                            concretetype=lltype.typeOf(fspecptr))]
        newargs += self.expand_nodes(newnodes)
        newresult = self.make_rt_result(op.result)
        newop = SpaceOperation('direct_call', newargs, newresult)
        return [newop]

    def handle_inlined_call(self, myframe, graph, newnodes):
        assert len(graph.getargs()) == len(newnodes)
        targetnodes = dict(zip(graph.getargs(), newnodes))
        calleeframe = VirtualFrame(graph, graph.startblock, 0,
                                   targetnodes, myframe)
        self.virtualframe = calleeframe
        self.nodes = calleeframe.get_nodes_in_use()
        return []


class FutureReturnValue(object):
    def __init__(self, op):
        self.op = op    # for debugging
    def getfrozenkey(self, memo):
        return None
    def accumulate_nodes(self, rtnodes, vtnodes):
        pass
    def copy(self, memo, flagreadonly):
        return self

# ____________________________________________________________
# helpers

def vars_alive_through_op(block, index):
    # NB. make sure this always returns the variables in the same order
    if len(block.exits) == 0:
        return block.inputargs   # return or except block
    result = []
    seen = {}
    def see(v):
        if isinstance(v, Variable) and v not in seen:
            result.append(v)
            seen[v] = True
    # don't include the variables produced by the current or future operations
    for op in block.operations[index:]:
        seen[op.result] = True
    # don't include the extra vars produced by exception-catching links
    for link in block.exits:
        for v in link.getextravars():
            seen[v] = True
    # but include the variables consumed by the current or any future operation
    for op in block.operations[index:]:
        for v in op.args:
            see(v)
    see(block.exitswitch)
    for link in block.exits:
        for v in link.args:
            see(v)
    return result

def is_return(block):
    return len(block.exits) == 0 and len(block.inputargs) == 1

def is_except(block):
    return len(block.exits) == 0 and len(block.inputargs) == 2
