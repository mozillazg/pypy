from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, FunctionGraph
from pypy.translator.backendopt.support import log
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype


# ____________________________________________________________


class CannotVirtualize(Exception):
    pass


class MallocVirtualizer(object):

    def __init__(self, graphs):
        self.graphs = graphs
        self.new_graphs = {}
        self.cache = BlockSpecCache()
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
        mallocspec = MallocSpecializer(self, op.result.concretetype.TO)
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
        self.specialized_blocks = {}
        self.block_keys = {}
        self.graph_starting_at = {}
        self.fallback = fallback

    def lookup_spec_block(self, block, extra_key):
        key = self.block_keys.get(block, frozenset())
        key = key.union([extra_key])
        try:
            return self.specialized_blocks[key]
        except KeyError:
            if self.fallback is None:
                return None
            else:
                return self.fallback.specialized_blocks.get(key)

    def remember_spec_block(self, block, extra_key, specblock):
        key = self.block_keys.get(block, frozenset())
        key = key.union([extra_key])
        self.specialized_blocks[key] = specblock
        self.block_keys[specblock] = key

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
        self.fallback.block_keys.update(self.block_keys)
        self.fallback.graph_starting_at.update(self.graph_starting_at)


class MallocSpecializer(object):

    def __init__(self, mallocv, MALLOCTYPE):
        self.mallocv = mallocv
        self.MALLOCTYPE = MALLOCTYPE
        self.names_and_types = []
        self.name2index = {}
        self.initialize_type(MALLOCTYPE)
        self.pending_specializations = []
        self.cache = BlockSpecCache(fallback=mallocv.cache)

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

    def remove_malloc(self, block, v_result):
        self.startblock = block
        spec = BlockSpecializer(self, v_result)
        spec.initialize_renamings(block.inputargs)
        self.newinputargs = spec.expand_vars(block.inputargs)
        self.newoperations = spec.specialize_operations(block.operations)
        self.newexits = self.follow_exits(block, spec)

    def follow_exits(self, block, spec):
        newlinks = []
        for link in block.exits:
            targetblock = link.target
            for v1, v2 in zip(link.args, link.target.inputargs):
                if v1 in spec.curvars:
                    targetblock = self.get_specialized_block(targetblock, v2)
            newlink = Link(spec.expand_vars(link.args), targetblock)
            newlinks.append(newlink)
        return newlinks

    def get_specialized_block(self, block, v):
        specblock = self.cache.lookup_spec_block(block, (self.MALLOCTYPE, v))
        if specblock is None:
            if block.operations == ():
                raise CannotVirtualize("return or except block")
            spec = BlockSpecializer(self, v)
            spec.make_expanded_vars()
            spec.initialize_renamings(block.inputargs)
            specblock = Block(spec.expand_vars(block.inputargs))
            self.pending_specializations.append((spec, block, specblock))
            self.cache.remember_spec_block(block, (self.MALLOCTYPE, v),
                                           specblock)
        return specblock

    def get_specialized_graph(self, graph, v):
        block = graph.startblock
        specblock = self.get_specialized_block(block, v)
        specgraph = self.cache.lookup_graph_starting_at(specblock)
        if specgraph is None:
            specgraph = FunctionGraph(graph.name + '_spec', specblock)
            self.cache.remember_graph_starting_at(specblock, specgraph)
        return specgraph

    def propagate_specializations(self):
        while self.pending_specializations:
            spec, block, specblock = self.pending_specializations.pop()
            specblock.operations = spec.specialize_operations(block.operations)
            specblock.closeblock(*self.follow_exits(block, spec))

    def commit(self):
        self.startblock.inputargs = self.newinputargs
        self.startblock.operations = self.newoperations
        self.startblock.recloseblock(*self.newexits)
        self.cache.push_changes()


class BlockSpecializer(object):

    def __init__(self, mallocspec, v):
        self.mallocspec = mallocspec
        self.curvars = set([v])

    def make_expanded_vars(self):
        self.expanded_v = []
        for name, FIELDTYPE in self.mallocspec.names_and_types:
            v = Variable(name)
            v.concretetype = FIELDTYPE
            self.expanded_v.append(v)

    def make_expanded_zero_constants(self):
        self.expanded_v = []
        for name, FIELDTYPE in self.mallocspec.names_and_types:
            c = Constant(FIELDTYPE._defl())
            c.concretetype = FIELDTYPE
            self.expanded_v.append(c)

    def rename_nonvirtual(self, v, where=None):
        if isinstance(v, Constant):
            return v
        if v in self.curvars:
            raise CannotVirtualize(where)
        [v2] = self.renamings[v]
        return v2

    def expand_vars(self, vars):
        result_v = []
        for v in vars:
            result_v += self.renamings[v]
        return result_v

    def initialize_renamings(self, inputargs):
        self.renamings = {}
        for v in inputargs:
            if v in self.curvars:
                self.renamings[v] = self.expanded_v
            else:
                v2 = Variable(v)
                v2.concretetype = v.concretetype
                self.renamings[v] = [v2]

    def specialize_operations(self, operations):
        newoperations = []
        for op in operations:
            meth = getattr(self, 'handle_op_' + op.opname,
                           self.handle_default)
            newoperations += meth(op)
        return newoperations

    def handle_default(self, op):
        newargs = [self.rename_nonvirtual(v, op) for v in op.args]
        newresult = Variable(op.result)
        newresult.concretetype = op.result.concretetype
        self.renamings[op.result] = [newresult]
        return [SpaceOperation(op.opname, newargs, newresult)]

    def handle_op_getfield(self, op):
        if op.args[0] in self.curvars:
            fieldname = op.args[1].value
            index = self.mallocspec.name2index[fieldname]
            v_field = self.expanded_v[index]
            self.renamings[op.result] = [v_field]
            return []
        else:
            return self.handle_default(op)

    def handle_op_setfield(self, op):
        if op.args[0] in self.curvars:
            fieldname = op.args[1].value
            index = self.mallocspec.name2index[fieldname]
            self.expanded_v[index] = self.rename_nonvirtual(op.args[2], op)
            return []
        else:
            return self.handle_default(op)

    def handle_op_malloc(self, op):
        if op.result in self.curvars:
            self.make_expanded_zero_constants()
            self.renamings[op.result] = self.expanded_v
            return []
        else:
            return self.handle_default(op)

    def handle_op_direct_call(self, op):
        fobj = op.args[0].value._obj
        if hasattr(fobj, 'graph'):
            graph = fobj.graph
            nb_args = len(op.args) - 1
            assert nb_args == len(graph.getargs())
            newargs = []
            for i in range(nb_args):
                v1 = op.args[1+i]
                if v1 not in self.curvars:
                    newargs.append(v1)
                else:
                    inputarg_index_in_specgraph = len(newargs)
                    v2 = graph.getargs()[inputarg_index_in_specgraph]
                    assert v1.concretetype == v2.concretetype
                    specgraph = self.mallocspec.get_specialized_graph(graph,
                                                                      v2)
                    newargs.extend(self.expanded_v)
                    graph = specgraph
            assert len(newargs) == len(graph.getargs())
            fspecptr = getfunctionptr(graph)
            newargs.insert(0, Constant(fspecptr,
                                       concretetype=lltype.typeOf(fspecptr)))
            newresult = Variable(op.result)
            newresult.concretetype = op.result.concretetype
            self.renamings[op.result] = [newresult]
            newop = SpaceOperation('direct_call', newargs, newresult)
            return [newop]
        else:
            return self.handle_default(op)
