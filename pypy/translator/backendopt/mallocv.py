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

    def getfrozenkey(self, memo):
        return 'R'

    def find_rt_nodes(self, memo, result):
        result.append(self)

    def copy(self, function, name, TYPE, memo):
        return function(name, TYPE)

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

    def find_rt_nodes(self, memo, result):
        if self in memo:
            return
        memo[self] = True
        for subnode in self.fields:
            subnode.find_rt_nodes(memo, result)

    def copy(self, function, _name, _TYPE, memo):
        if self in memo:
            return memo[self]
        newnode = VirtualSpecNode(self.typedesc, [])
        memo[self] = newnode
        for (name, FIELDTYPE), subnode in zip(self.typedesc.names_and_types,
                                              self.fields):
            newsubnode = subnode.copy(function, name, FIELDTYPE, memo)
            newnode.fields.append(newsubnode)
        return newnode

    def contains_mutable(self):
        if not self.typedesc.immutable_struct:
            return True
        for subnode in self.fields:
            if subnode.contains_mutable():
                return True
        return False


def getfrozenkey(nodelist):
    memo = {}
    return tuple([node.getfrozenkey(memo) for node in nodelist])

def find_rt_nodes(nodelist):
    result = []
    memo = {}
    for node in nodelist:
        node.find_rt_nodes(memo, result)
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
        self.specialized_blocks = {}  # {(org Block, frozenkey): spec Block}
        self.graph_starting_at = {}   # {spec Block: spec Graph}
        self.fallback = fallback

    def lookup_spec_block(self, orgblock, nodelist):
        if is_trivial_nodelist(nodelist):
            return orgblock
        key = orgblock, getfrozenkey(nodelist)
        try:
            return self.specialized_blocks[key]
        except KeyError:
            if self.fallback is None:
                return None
            else:
                return self.fallback.specialized_blocks.get(key)

    def remember_spec_block(self, orgblock, nodelist, specblock):
        assert len(nodelist) == len(orgblock.inputargs)
        key = orgblock, getfrozenkey(nodelist)
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
        trivialnodelist = [RuntimeSpecNode() for v in block.inputargs]
        spec.initialize_renamings(block.inputargs, trivialnodelist)
        self.newinputargs = spec.expand_vars(block.inputargs)
        self.newoperations = spec.specialize_operations(block.operations)
        self.newexitswitch = spec.rename_nonvirtual(block.exitswitch,
                                                    'exitswitch')
        self.newexits = self.follow_exits(block, spec)

    def follow_exits(self, block, spec):
        newlinks = []
        for link in block.exits:
            targetnodes = [spec.getnode(v) for v in link.args]
            specblock = self.get_specialized_block(link.target, targetnodes)
            newlink = Link(spec.expand_vars(link.args), specblock)
            newlink.exitcase = link.exitcase
            newlink.llexitcase = link.llexitcase
            newlinks.append(newlink)
        return newlinks

    def get_specialized_block(self, orgblock, nodelist):
        specblock = self.cache.lookup_spec_block(orgblock, nodelist)
        if specblock is None:
            if orgblock.operations == ():
                raise CannotVirtualize("return or except block")
            spec = BlockSpecializer(self)
            spec.initialize_renamings(orgblock.inputargs, nodelist)
            specblock = Block(spec.expand_vars(orgblock.inputargs))
            self.pending_specializations.append((spec, orgblock, specblock))
            self.cache.remember_spec_block(orgblock, nodelist, specblock)
        return specblock

    def get_specialized_graph(self, graph, v):
        block = graph.startblock
        specblock = self.get_specialized_block(block, v)
        if specblock is block:
            return graph
        specgraph = self.cache.lookup_graph_starting_at(specblock)
        if specgraph is None:
            specgraph = FunctionGraph(graph.name + '_spec', specblock)
            self.cache.remember_graph_starting_at(specblock, specgraph)
        return specgraph

    def propagate_specializations(self):
        while self.pending_specializations:
            spec, block, specblock = self.pending_specializations.pop()
            specblock.operations = spec.specialize_operations(block.operations)
            specblock.exitswitch = spec.rename_nonvirtual(block.exitswitch,
                                                          'exitswitch')
            specblock.closeblock(*self.follow_exits(block, spec))

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

    def initialize_renamings(self, inputargs, inputnodes):
        assert len(inputargs) == len(inputnodes)
        self.nodes = {}
        self.renamings = {}    # {RuntimeSpecNode(): Variable()}
        memo = {}
        for v, node in zip(inputargs, inputnodes):
            newnode = node.copy(self.fresh_rtnode, v, v.concretetype, memo)
            self.setnode(v, newnode)

    def setnode(self, v, node):
        assert v not in self.nodes
        self.nodes[v] = node

    def getnode(self, v):
        if isinstance(v, Variable):
            return self.nodes[v]
        else:
            rtnode = RuntimeSpecNode()
            self.renamings[rtnode] = v
            return rtnode

    def rename_nonvirtual(self, v, where=None):
        if not isinstance(v, Variable):
            return v
        node = self.nodes[v]
        if not isinstance(node, RuntimeSpecNode):
            raise CannotVirtualize(where)
        return self.renamings[node]

    def expand_vars(self, vars):
        nodelist = [self.getnode(v) for v in vars]
        rtnodes = find_rt_nodes(nodelist)
        return [self.renamings[rtnode] for rtnode in rtnodes]

    def specialize_operations(self, operations):
        newoperations = []
        for op in operations:
            meth = getattr(self, 'handle_op_' + op.opname,
                           self.handle_default)
            newoperations += meth(op)
        return newoperations

    def fresh_rtnode(self, name, TYPE):
        newvar = Variable(name)
        newvar.concretetype = TYPE
        newrtnode = RuntimeSpecNode()
        self.renamings[newrtnode] = newvar
        return newrtnode

    def make_rt_result(self, v_result):
        rtnode = self.fresh_rtnode(v_result, v_result.concretetype)
        self.setnode(v_result, rtnode)
        return self.renamings[rtnode]

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
                fieldnode = RuntimeSpecNode()
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
            return self.handle_default(op)
        newgraph = self.mallocspec.get_specialized_graph(graph, newnodes)
        if newgraph is graph:
            return self.handle_default(op)
        fspecptr = getfunctionptr(newgraph)
        newargs = [Constant(fspecptr,
                            concretetype=lltype.typeOf(fspecptr))]
        newargs += self.expand_vars(op.args[1:])
        newresult = self.make_rt_result(op.result)
        newop = SpaceOperation('direct_call', newargs, newresult)
        return [newop]
