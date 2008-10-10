from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph
from pypy.translator.backendopt.support import log
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype


# ____________________________________________________________


class MallocTypeDesc(object):

    def __init__(self, MALLOCTYPE):
        self.MALLOCTYPE = MALLOCTYPE
        self.names_and_types = []
        self.name2index = {}
        self.initialize_type(MALLOCTYPE)
        #self.immutable_struct = MALLOCTYPE._hints.get('immutable')

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

    def __init__(self, sourceblock, nextopindex, allnodes, callerframe=None):
        self.varlist = vars_alive_through_op(sourceblock, nextopindex)
        self.nodelist = [allnodes[v] for v in self.varlist]
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

    def return_to_caller(self, returnblock, targetnodes):
        [v_ret] = returnblock.inputargs
        retnode = targetnodes[v_ret]
        callerframe = self.callerframe
        for i in range(len(callerframe.nodelist)):
            if isinstance(callerframe.nodelist[i], FutureReturnValue):
                callerframe.nodelist[i] = retnode
        return callerframe


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


class MallocVirtualizer(object):

    def __init__(self, graphs, verbose=False):
        self.graphs = graphs
        self.graphbuilders = {}
        self.specialized_graphs = FrameKeyCache()
        self.malloctypedescs = {}
        self.count_virtualized = 0
        self.verbose = verbose

    def report_result(self):
        log.mallocv('removed %d mallocs so far' % (self.count_virtualized,))
        return self.count_virtualized

    def find_all_mallocs(self, graph):
        result = []
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'malloc':
                    result.append((block, op))
        return result

    def remove_mallocs_once(self):
        prev = self.count_virtualized
        for graph in self.graphs:
            all_blocks = None
            all_mallocs = self.find_all_mallocs(graph)
            for block, op in all_mallocs:
                if all_blocks is None:
                    all_blocks = set(graph.iterblocks())
                if block not in all_blocks:
                    continue   # this block was removed from the graph
                               # by a previous try_remove_malloc()
                try:
                    self.try_remove_malloc(graph, block, op)
                except CannotVirtualize, e:
                    if self.verbose:
                        log.mallocv('%s failed: %s' % (op.result, e))
                else:
                    if self.verbose:
                        log.mallocv('%s removed' % (op.result,))
                    all_blocks = None
        progress = self.report_result() - prev
        return progress

    def getmalloctypedesc(self, MALLOCTYPE):
        try:
            dsc = self.malloctypedescs[MALLOCTYPE]
        except KeyError:
            dsc = self.malloctypedescs[MALLOCTYPE] = MallocTypeDesc(MALLOCTYPE)
        return dsc

    def try_remove_malloc(self, graph, block, op):
        graphbuilder = GraphBuilder(self)
        if graph in self.graphbuilders:
            graphbuilder.initialize_from_old_builder(self.graphbuilders[graph])
        graphbuilder.start_from_a_malloc(block, op.result)
        graphbuilder.propagate_specializations()
        # if we reach this point without a CannotVirtualize, success
        graphbuilder.finished_removing_malloc()
        self.graphbuilders[graph] = graphbuilder
        self.count_virtualized += 1

    def get_specialized_graph(self, graph, nodelist):
        assert len(graph.getargs()) == len(nodelist)
        if is_trivial_nodelist(nodelist):
            return 'trivial', graph
        nodes = dict(zip(graph.getargs(), nodelist))
        virtualframe = VirtualFrame(graph.startblock, 0, nodes)
        try:
            return self.specialized_graphs.getitem(virtualframe)
        except KeyError:
            self.build_specialized_graph(graph, virtualframe)
            return self.specialized_graphs.getitem(virtualframe)

    def build_specialized_graph(self, graph, virtualframe):
        graphbuilder = GraphBuilder(self)
        specblock = graphbuilder.start_from_virtualframe(virtualframe)
        specgraph = FunctionGraph(graph.name + '_mallocv', specblock)
        self.specialized_graphs.setitem(virtualframe, ('call', specgraph))
        try:
            graphbuilder.propagate_specializations()
        except ForcedInline, e:
            if self.verbose:
                log.mallocv('%s inlined: %s' % (graph.name, e))
            self.specialized_graphs.setitem(virtualframe, ('inline', None))
        except CannotVirtualize, e:
            if self.verbose:
                log.mallocv('%s failing: %s' % (graph.name, e))
            self.specialized_graphs.setitem(virtualframe, ('fail', None))
        else:
            self.graphbuilders[specgraph] = graphbuilder
            self.graphs.append(specgraph)


class FrameKeyCache(object):

    def __init__(self):
        self.content = {}

    def get(self, virtualframe):
        key = virtualframe.getfrozenkey()
        return self.content.get(key)

    def getitem(self, virtualframe):
        key = virtualframe.getfrozenkey()
        return self.content[key]

    def setitem(self, virtualframe, value):
        key = virtualframe.getfrozenkey()
        self.content[key] = value

    def update(self, other):
        self.content.update(other.content)


class GraphBuilder(object):

    def __init__(self, mallocv):
        self.mallocv = mallocv
        self.specialized_blocks = FrameKeyCache()
        self.pending_specializations = []

    def initialize_from_old_builder(self, oldbuilder):
        self.specialized_blocks.update(oldbuilder.specialized_blocks)

    def start_from_virtualframe(self, startframe):
        spec = BlockSpecializer(self)
        spec.initialize_renamings(startframe)
        self.pending_specializations.append(spec)
        return spec.specblock

    def start_from_a_malloc(self, block, v_result):
        nodes = {}
        for v in block.inputargs:
            nodes[v] = RuntimeSpecNode(v, v.concretetype)
        trivialframe = VirtualFrame(block, 0, nodes)
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

    def get_specialized_block(self, virtualframe):
        specblock = self.specialized_blocks.get(virtualframe)
        if specblock is None:
            orgblock = virtualframe.sourceblock
            assert len(orgblock.exits) != 0
            spec = BlockSpecializer(self)
            spec.initialize_renamings(virtualframe)
            self.pending_specializations.append(spec)
            specblock = spec.specblock
            self.specialized_blocks.setitem(virtualframe, specblock)
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
        currentframe = self.virtualframe
        block = currentframe.sourceblock
        self.specblock.exitswitch = self.rename_nonvirtual(block.exitswitch,
                                                           'exitswitch')
        newlinks = []
        for link in block.exits:
            targetnodes = {}

            rtnodes = []
            for v1, v2 in zip(link.args, link.target.inputargs):
                node = self.getnode(v1)
                if isinstance(node, RuntimeSpecNode):
                    rtnodes.append(node)
                targetnodes[v2] = node

            if (len(rtnodes) == len(link.args) and
                currentframe.callerframe is None):
                # there is no more VirtualSpecNodes being passed around,
                # so we can stop specializing.
                specblock = link.target
            else:
                if len(link.target.exits) == 0:    # return or except block
                    if currentframe.callerframe is None:
                        raise CannotVirtualize("return or except block")
                    newframe = currentframe.return_to_caller(link.target,
                                                             targetnodes)
                else:
                    newframe = VirtualFrame(link.target, 0, targetnodes,
                                          callerframe=currentframe.callerframe)
                rtnodes = newframe.find_rt_nodes()
                specblock = self.graphbuilder.get_specialized_block(newframe)

            linkargs = [self.renamings[rtnode] for rtnode in rtnodes]
            newlink = Link(linkargs, specblock)
            newlink.exitcase = link.exitcase
            newlink.llexitcase = link.llexitcase
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
        argnodes = copynodes(newnodes, flagreadonly=myframe.find_vt_nodes())
        mallocv = self.graphbuilder.mallocv
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
        sourceblock = self.virtualframe.sourceblock
        nextopindex = self.virtualframe.nextopindex
        self.nodes[op.result] = FutureReturnValue(op)
        myframe = VirtualFrame(sourceblock, nextopindex,
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
        calleeframe = VirtualFrame(graph.startblock, 0,
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
    # but include the variables consumed by the current or any future operation
    for op in block.operations[index:]:
        for v in op.args:
            see(v)
    see(block.exitswitch)
    for link in block.exits:
        for v in link.args:
            see(v)
    return result
