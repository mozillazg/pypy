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
        self.immutable_struct = MALLOCTYPE._hints.get('immutable')

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

    def accumulate_rt_nodes(self, memo, result):
        result.append(self)

    def copy(self, memo):
        return RuntimeSpecNode(self.name, self.TYPE)

    def contains_mutable(self):
        return False


class VirtualSpecNode(SpecNode):

    def __init__(self, typedesc, fields):
        self.typedesc = typedesc
        self.fields = fields     # list of SpecNodes

    def getfrozenkey(self, memo):
        if self in memo:
            return memo[self]
        else:
            memo[self] = len(memo)
            result = [self.typedesc]
            for subnode in self.fields:
                result.append(subnode.getfrozenkey(memo))
            return tuple(result)

    def accumulate_rt_nodes(self, memo, result):
        if self in memo:
            return
        memo[self] = True
        for subnode in self.fields:
            subnode.accumulate_rt_nodes(memo, result)

    def copy(self, memo):
        if self in memo:
            return memo[self]
        newnode = VirtualSpecNode(self.typedesc, [])
        memo[self] = newnode
        for subnode in self.fields:
            newnode.fields.append(subnode.copy(memo))
        return newnode

    def contains_mutable(self):
        if not self.typedesc.immutable_struct:
            return True
        for subnode in self.fields:
            if subnode.contains_mutable():
                return True
        return False


class VirtualFrame(object):

    def __init__(self, sourceblock, nextopindex, allnodes, callerframe=None):
        self.varlist = vars_alive_through_op(sourceblock, nextopindex)
        self.nodelist = [allnodes[v] for v in self.varlist]
        self.sourceblock = sourceblock
        self.nextopindex = nextopindex
        self.callerframe = callerframe

    def get_nodes_in_use(self):
        return dict(zip(self.varlist, self.nodelist))

    def copy(self, memo):
        newframe = VirtualFrame.__new__(VirtualFrame)
        newframe.varlist = self.varlist
        newframe.nodelist = [node.copy(memo) for node in self.nodelist]
        newframe.sourceblock = self.sourceblock
        newframe.nextopindex = self.nextopindex
        if self.callerframe is None:
            newframe.callerframe = None
        else:
            newframe.callerframe = self.callerframe.copy(memo)
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

    def find_rt_nodes(self):
        result = []
        memo = {}
        for frame in self.enum_call_stack():
            for node in frame.nodelist:
                node.accumulate_rt_nodes(memo, result)
        return result


def is_trivial_nodelist(nodelist):
    for node in nodelist:
        if not isinstance(node, RuntimeSpecNode):
            return False
    return True

def contains_mutable(nodelist):
    for node in nodelist:
        if node.contains_mutable():
            return True
    return False


class CannotVirtualize(Exception):
    pass


class MallocVirtualizer(object):

    def __init__(self, graphs):
        self.graphs = graphs
        self.new_graphs = {}
        self.cache = BlockSpecCache()
        self.malloctypedescs = {}
        self.count_virtualized = 0

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

    def remove_mallocs_once(self, verbose=False):
        prev = self.count_virtualized
        for graph in self.graphs:
            all_mallocs = self.find_all_mallocs(graph)
            for block, op in all_mallocs:
                try:
                    self.try_remove_malloc(block, op)
                    if verbose:
                        log.mallocv('%s removed' % (op.result,))
                    break    # don't continue on this graph, which was mutated
                except CannotVirtualize, e:
                    if verbose:
                        log.mallocv('%s failed: %s' % (op.result, e))
        self.put_new_graphs_back_in_translator()
        progress = self.report_result() - prev
        return progress

    def try_remove_malloc(self, block, op):
        MALLOCTYPE = op.result.concretetype.TO
        try:
            dsc = self.malloctypedescs[MALLOCTYPE]
        except KeyError:
            dsc = self.malloctypedescs[MALLOCTYPE] = MallocTypeDesc(MALLOCTYPE)
        mallocspec = MallocSpecializer(self, dsc)
        mallocspec.remove_malloc(block, op.result)
        mallocspec.propagate_specializations()
        # if we read this point without a CannotVirtualize, success
        mallocspec.commit()
        self.count_virtualized += 1

    def put_new_graphs_back_in_translator(self):
        for graph in self.cache.graph_starting_at.values():
            if graph not in self.new_graphs:
                self.new_graphs[graph] = True
                self.graphs.append(graph)


class BlockSpecCache(object):

    def __init__(self, fallback=None):
        self.specialized_blocks = {}  # {frame_frozen_key: spec Block}
        self.graph_starting_at = {}   # {spec Block: spec Graph}
        self.fallback = fallback

    def lookup_spec_block(self, virtualframe):
        key = virtualframe.getfrozenkey()
        try:
            return self.specialized_blocks[key]
        except KeyError:
            if self.fallback is None:
                return None
            else:
                return self.fallback.specialized_blocks.get(key)

    def remember_spec_block(self, virtualframe, specblock):
        key = virtualframe.getfrozenkey()
        self.specialized_blocks[key] = specblock

    def lookup_graph_starting_at(self, startblock):
        try:
            return self.graph_starting_at[startblock]
        except KeyError:
            if self.fallback is None:
                return None
            else:
                return self.fallback.graph_starting_at.get(startblock)

    def remember_graph_starting_at(self, startblock, graph):
        self.graph_starting_at[startblock] = graph

    def push_changes(self):
        self.fallback.specialized_blocks.update(self.specialized_blocks)
        self.fallback.graph_starting_at.update(self.graph_starting_at)


class MallocSpecializer(object):

    def __init__(self, mallocv, malloctypedesc):
        self.mallocv = mallocv
        self.malloctypedesc = malloctypedesc
        self.pending_specializations = []
        self.cache = BlockSpecCache(fallback=mallocv.cache)

    def remove_malloc(self, block, v_result):
        self.startblock = block
        spec = BlockSpecializer(self, v_result)
        nodes = {}
        for v in block.inputargs:
            nodes[v] = RuntimeSpecNode(v, v.concretetype)
        trivialframe = VirtualFrame(block, 0, nodes)
        self.newinputargs = spec.initialize_renamings(trivialframe)
        self.newoperations = spec.specialize_operations()
        self.newexitswitch, self.newexits = self.follow_exits(spec)

    def follow_exits(self, spec):
        currentframe = spec.virtualframe
        block = currentframe.sourceblock
        v_exitswitch = spec.rename_nonvirtual(block.exitswitch,
                                              'exitswitch')
        newlinks = []
        for link in block.exits:
            targetnodes = {}

            rtnodes = []
            for v1, v2 in zip(link.args, link.target.inputargs):
                node = spec.getnode(v1)
                if isinstance(node, RuntimeSpecNode):
                    rtnodes.append(node)
                targetnodes[v2] = node

            if (len(rtnodes) == len(link.args) and
                currentframe.callerframe is None):
                # there is no more VirtualSpecNodes being passed around,
                # so we can stop specializing.
                specblock = link.target
            else:
                newframe = VirtualFrame(link.target, 0, targetnodes,
                                        callerframe=currentframe.callerframe)
                rtnodes = newframe.find_rt_nodes()
                specblock = self.get_specialized_block(newframe)

            linkargs = [spec.renamings[rtnode] for rtnode in rtnodes]
            newlink = Link(linkargs, specblock)
            newlink.exitcase = link.exitcase
            newlink.llexitcase = link.llexitcase
            newlinks.append(newlink)
        return v_exitswitch, newlinks

    def get_specialized_block(self, virtualframe):
        specblock = self.cache.lookup_spec_block(virtualframe)
        if specblock is None:
            orgblock = virtualframe.sourceblock
            if len(orgblock.exits) == 0:
                if virtualframe.callerframe is None:
                    raise CannotVirtualize("return or except block")
                else:
                    return self.get_specialized_block(virtualframe.callerframe)
            spec = BlockSpecializer(self)
            specinputargs = spec.initialize_renamings(virtualframe.copy({}))
            specblock = Block(specinputargs)
            self.pending_specializations.append((spec, specblock))
            self.cache.remember_spec_block(virtualframe, specblock)
        return specblock

    def get_specialized_graph(self, graph, nodelist):
        if is_trivial_nodelist(nodelist):
            return graph
        block = graph.startblock
        assert len(graph.getargs()) == len(nodelist)
        nodes = dict(zip(graph.getargs(), nodelist))
        virtualframe = VirtualFrame(block, 0, nodes)
        specblock = self.get_specialized_block(virtualframe)
        specgraph = self.cache.lookup_graph_starting_at(specblock)
        if specgraph is None:
            specgraph = FunctionGraph(graph.name + '_mallocv', specblock)
            self.cache.remember_graph_starting_at(specblock, specgraph)
        return specgraph

    def propagate_specializations(self):
        while self.pending_specializations:
            spec, specblock = self.pending_specializations.pop()
            specblock.operations = spec.specialize_operations()
            specblock.exitswitch, newlinks = self.follow_exits(spec)
            specblock.closeblock(*newlinks)

    def commit(self):
        self.startblock.inputargs = self.newinputargs
        self.startblock.operations = self.newoperations
        self.startblock.exitswitch = self.newexitswitch
        self.startblock.recloseblock(*self.newexits)
        self.cache.push_changes()


class BlockSpecializer(object):

    def __init__(self, mallocspec, v_expand_malloc=None):
        self.mallocspec = mallocspec
        self.v_expand_malloc = v_expand_malloc

    def initialize_renamings(self, virtualframe):
        # the caller is responsible for making a copy of 'virtualframe'
        # if needed, because the BlockSpecializer will mutate some of its
        # content.
        self.virtualframe = virtualframe
        self.nodes = virtualframe.get_nodes_in_use()
        self.renamings = {}    # {RuntimeSpecNode(): Variable()}
        result = []
        for rtnode in virtualframe.find_rt_nodes():
            v = rtnode.newvar()
            self.renamings[rtnode] = v
            result.append(v)
        return result

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
        memo = {}
        rtnodes = []
        for node in nodelist:
            node.accumulate_rt_nodes(memo, rtnodes)
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
        return newoperations

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
            fieldname = op.args[1].value
            index = node.typedesc.name2index[fieldname]
            node.fields[index] = self.getnode(op.args[2])
            return []
        else:
            return self.handle_default(op)

    def handle_op_malloc(self, op):
        if op.result is self.v_expand_malloc:
            typedesc = self.mallocspec.malloctypedesc
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
        if contains_mutable(newnodes):
            return self.handle_mutable_call(op, graph, newnodes)
        else:
            return self.handle_immutable_call(op, graph, newnodes)

    def handle_immutable_call(self, op, graph, newnodes):
        newgraph = self.mallocspec.get_specialized_graph(graph, newnodes)
        if newgraph is graph:
            return self.handle_default(op)
        fspecptr = getfunctionptr(newgraph)
        newargs = [Constant(fspecptr,
                            concretetype=lltype.typeOf(fspecptr))]
        newargs += self.expand_nodes(newnodes)
        newresult = self.make_rt_result(op.result)
        newop = SpaceOperation('direct_call', newargs, newresult)
        return [newop]

    def handle_mutable_call(self, op, graph, newnodes):
        sourceblock = self.virtualframe.sourceblock
        nextopindex = self.virtualframe.nextopindex
        myframe = VirtualFrame(sourceblock, nextopindex,
                               self.nodes,
                               self.virtualframe.callerframe)
        assert len(graph.getargs()) == len(newnodes)
        targetnodes = dict(zip(graph.getargs(), newnodes))
        calleeframe = VirtualFrame(graph.startblock, 0,
                                   targetnodes, myframe)
        self.virtualframe = calleeframe
        self.nodes = calleeframe.get_nodes_in_use()
        return []

# ____________________________________________________________
# helpers

def vars_alive_through_op(block, index):
    # NB. make sure this always returns the variables in the same order
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
