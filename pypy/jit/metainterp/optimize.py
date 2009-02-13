from pypy.jit.metainterp.history import (Box, Const, ConstInt,
                                         MergePoint, ResOperation, Jump)
from pypy.jit.metainterp.heaptracker import always_pure_operations
from pypy.jit.metainterp.specnode import (FixedClassSpecNode,
                                          VirtualInstanceSpecNode,
                                          VirtualizableSpecNode,
                                          NotSpecNode)

class CancelInefficientLoop(Exception):
    pass

class AllocationStorage(object):
    def __init__(self):
        # allocations: list of vtables to allocate
        # setfields: list of triples
        #                 (index_in_allocations, ofs, ~index_in_arglist)
        #                  -or-
        #                 (index_in_allocations, ofs, index_in_allocations)
        #                  -or-
        #                 (~index_in_arglist, ofs, index_in_allocations)
        #                  -or-
        #                 (~index_in_arglist, ofs, ~index_in_arglist)
        # last two cases are for virtualizables only
        self.allocations = []
        self.setfields = []

    def deal_with_box(self, box, nodes, liveboxes, memo):
        if isinstance(box, Const):
            virtual = False
            virtualized = False
        else:
            instnode = nodes[box]
            box = instnode.source
            if box in memo:
                return memo[box]
            virtual = instnode.virtual
            virtualized = instnode.virtualized
        if virtual:
            alloc_offset = len(self.allocations)
            self.allocations.append(instnode.cls.source.getint())
            res = alloc_offset
            memo[box] = res
            for ofs, node in instnode.curfields.items():
                num = self.deal_with_box(node.source, nodes, liveboxes, memo)
                self.setfields.append((alloc_offset, ofs, num))
        elif virtualized:
            res = ~len(liveboxes)
            memo[box] = res
            liveboxes.append(box)
            for ofs, node in instnode.curfields.items():
                num = self.deal_with_box(node.source, nodes, liveboxes, memo)
                self.setfields.append((res, ofs, num))
        else:
            res = ~len(liveboxes)
            memo[box] = res
            liveboxes.append(box)
        return res

class TypeCache(object):
    pass
type_cache = TypeCache()   # XXX remove me later
type_cache.class_size = {}

class InstanceNode(object):
    def __init__(self, source, escaped=True, startbox=False, const=False):
        self.source = source       # a Box
        self.escaped = escaped
        self.startbox = startbox
        self.const = const
        self.virtual = False
        self.virtualized = False
        self.cls = None
        self.origfields = {}
        self.curfields = {}

    def escape_if_startbox(self, memo):
        if self in memo:
            return
        memo[self] = None
        if self.startbox:
            self.escaped = True
        for node in self.curfields.values():
            node.escape_if_startbox(memo)

    def add_to_dependency_graph(self, other, dep_graph):
        dep_graph.append((self, other))
        for ofs, node in self.origfields.items():
            if ofs in other.curfields:
                node.add_to_dependency_graph(other.curfields[ofs], dep_graph)

    def intersect(self, other):
        if not other.cls:
            return NotSpecNode()
        if self.cls:
            if not self.cls.source.equals(other.cls.source):
                raise CancelInefficientLoop
            known_class = self.cls.source
        else:
            known_class = other.cls.source
        if other.escaped and not other.virtualized:
            if self.cls is None:
                return NotSpecNode()
            return FixedClassSpecNode(known_class)
        if not other.escaped:
            fields = []
            lst = other.curfields.items()
            lst.sort()
            for ofs, node in lst:
                if ofs in self.origfields:
                    specnode = self.origfields[ofs].intersect(node)
                else:
                    self.origfields[ofs] = InstanceNode(node.source.clonebox())
                    specnode = NotSpecNode()
                fields.append((ofs, specnode))
            return VirtualInstanceSpecNode(known_class, fields)
        else:
            assert self is other
            d = self.origfields.copy()
            d.update(other.curfields)
            offsets = d.keys()
            offsets.sort()
            fields = []
            for ofs in offsets:
                if ofs in self.origfields and ofs in other.curfields:
                    node = other.curfields[ofs]
                    specnode = self.origfields[ofs].intersect(node)
                elif ofs in self.origfields:
                    specnode = NotSpecNode()
                else:
                    # ofs in other.curfields
                    node = other.curfields[ofs]
                    self.origfields[ofs] = InstanceNode(node.source.clonebox())
                    specnode = NotSpecNode()
                fields.append((ofs, specnode))
                    
            return VirtualizableSpecNode(known_class, fields)

    def __repr__(self):
        flags = ''
        if self.escaped:     flags += 'e'
        if self.startbox:    flags += 's'
        if self.const:       flags += 'c'
        if self.virtual:     flags += 'v'
        if self.virtualized: flags += 'V'
        return "<InstanceNode %s (%s)>" % (self.source, flags)


def optimize_loop(metainterp, old_loops, loop):
    if not metainterp._specialize:         # for tests only
        if old_loops:
            return old_loops[0]
        else:
            return None

    # This does "Perfect specialization" as per doc/jitpl5.txt.
    perfect_specializer = PerfectSpecializer(loop)
    perfect_specializer.find_nodes()
    perfect_specializer.intersect_input_and_output()
    for old_loop in old_loops:
        if perfect_specializer.match_exactly(old_loop):
            return old_loop
    perfect_specializer.optimize_loop()
    return None

def optimize_bridge(metainterp, old_loops, operations):
    if not metainterp._specialize:         # for tests only
        return old_loops[0]

    perfect_specializer = PerfectSpecializer(operations)
    perfect_specializer.find_nodes()
    for old_loop in old_loops:
        if perfect_specializer.match(old_loop.operations):
            perfect_specializer.adapt_for_match(old_loop.operations)
            perfect_specializer.optimize_loop()
            return old_loop
    return None     # no loop matches

class PerfectSpecializer(object):

    def __init__(self, loop):
        self.loop = loop
        self.nodes = {}
        self.dependency_graph = []

    def getnode(self, box):
        try:
            return self.nodes[box]
        except KeyError:
            assert isinstance(box, Const)
            node = self.nodes[box] = InstanceNode(box, escaped=True)
            return node

    def find_nodes(self):
        # Steps (1) and (2)
        for box in self.loop.operations[0].args:
            self.nodes[box] = InstanceNode(box, escaped=False, startbox=True)

        for op in self.loop.operations[1:-1]:
            opname = op.opname
            if opname == 'new_with_vtable':
                box = op.results[0]
                instnode = InstanceNode(box, escaped=False)
                instnode.cls = InstanceNode(op.args[1])
                self.nodes[box] = instnode
                continue
            elif opname == 'setfield_gc':
                instnode = self.getnode(op.args[0])
                fieldbox = op.args[1]
                assert isinstance(fieldbox, ConstInt)
                field = fieldbox.getint()
                fieldnode = self.getnode(op.args[2])
                instnode.curfields[field] = fieldnode
                self.dependency_graph.append((instnode, fieldnode))
                continue
            elif opname == 'getfield_gc':
                instnode = self.getnode(op.args[0])
                fieldbox = op.args[1]
                assert isinstance(fieldbox, ConstInt)
                field = fieldbox.getint()
                box = op.results[0]
                if field in instnode.curfields:
                    fieldnode = instnode.curfields[field]
                elif field in instnode.origfields:
                    fieldnode = instnode.origfields[field]
                else:
                    fieldnode = InstanceNode(box, escaped=False)
                    if instnode.startbox:
                        fieldnode.startbox = True
                    self.dependency_graph.append((instnode, fieldnode))
                    instnode.origfields[field] = fieldnode
                self.nodes[box] = fieldnode
                continue
            elif opname == 'guard_class':
                instnode = self.getnode(op.args[0])
                if instnode.cls is None:
                    instnode.cls = InstanceNode(op.args[1])
                continue
            elif opname == 'guard_nonvirtualized':
                instnode = self.getnode(op.args[0])
                if instnode.startbox:
                    instnode.virtualized = True
                if instnode.cls is None:
                    instnode.cls = InstanceNode(op.args[1])
                continue
            elif opname not in ('oois', 'ooisnot',
                                'ooisnull', 'oononnull'):
                # default case
                for box in op.args:
                    if isinstance(box, Box):
                        self.nodes[box].escaped = True
            for box in op.results:
                self.nodes[box] = InstanceNode(box, escaped=True)

    def recursively_find_escaping_values(self):
        assert self.loop.operations[0].opname == 'merge_point'
        end_args = self.loop.operations[-1].args
        memo = {}
        for i in range(len(end_args)):
            self.nodes[end_args[i]].escape_if_startbox(memo)
        for i in range(len(end_args)):
            box = self.loop.operations[0].args[i]
            other_box = end_args[i]
            self.nodes[box].add_to_dependency_graph(self.nodes[other_box],
                                                    self.dependency_graph)
        # XXX find efficient algorithm, we're too fried for that by now
        done = False
        while not done:
            done = True
            for instnode, fieldnode in self.dependency_graph:
                if instnode.escaped and not instnode.virtualized:
                    if not fieldnode.escaped:
                        fieldnode.escaped = True
                        done = False

    def intersect_input_and_output(self):
        # Step (3)
        self.recursively_find_escaping_values()
        mp = self.loop.operations[0]
        jump = self.loop.operations[-1]
        assert mp.opname == 'merge_point'
        assert jump.opname == 'jump'
        specnodes = []
        for i in range(len(mp.args)):
            enternode = self.nodes[mp.args[i]]
            leavenode = self.getnode(jump.args[i])
            specnodes.append(enternode.intersect(leavenode))
        self.specnodes = specnodes

    def expanded_version_of(self, boxlist):
        newboxlist = []
        assert len(boxlist) == len(self.specnodes)
        for i in range(len(boxlist)):
            box = boxlist[i]
            specnode = self.specnodes[i]
            specnode.expand_boxlist(self.nodes[box], newboxlist)
        return newboxlist

    def optimize_guard(self, op):
        liveboxes = []
        storage = AllocationStorage()
        memo = {}
        indices = []
        old_boxes = op.liveboxes
        op = op.clone()
        for box in old_boxes:
            indices.append(storage.deal_with_box(box, self.nodes,
                                                 liveboxes, memo))
        storage.indices = indices
        op.args = self.new_arguments(op)
        op.liveboxes = liveboxes
        op.storage_info = storage
        return op

    def new_arguments(self, op):
        newboxes = []
        for box in op.args:
            if isinstance(box, Box):
                instnode = self.nodes[box]
                assert not instnode.virtual
                box = instnode.source
            newboxes.append(box)
        return newboxes

    def replace_arguments(self, op):
        op = op.clone()
        op.args = self.new_arguments(op)
        return op

    def optimize_loop(self):
        newoperations = []
        mp = self.loop.operations[0]
        if mp.opname == 'merge_point':
            assert len(mp.args) == len(self.specnodes)
            for i in range(len(self.specnodes)):
                box = mp.args[i]
                self.specnodes[i].mutate_nodes(self.nodes[box])
        else:
            assert mp.opname == 'catch'
            for box in mp.args:
                self.nodes[box].cls = None
                assert not self.nodes[box].virtual

        for op in self.loop.operations:
            opname = op.opname
            if opname == 'merge_point':
                args = self.expanded_version_of(op.args)
                op = MergePoint('merge_point', args, [])
                newoperations.append(op)
                continue
            elif opname == 'jump':
                args = self.expanded_version_of(op.args)
                op = Jump('jump', args, [])
                newoperations.append(op)
                continue
            elif opname == 'guard_class':
                instnode = self.nodes[op.args[0]]
                if instnode.cls is not None:
                    assert op.args[1].equals(instnode.cls.source)
                    continue
                op = self.optimize_guard(op)
                newoperations.append(op)
                continue
            elif opname == 'guard_nonvirtualized':
                instnode = self.nodes[op.args[0]]
                if instnode.virtualized:
                    continue
                op = self.optimize_guard(op)
                newoperations.append(op)
                continue
            elif opname.startswith('guard_'):
                if opname == 'guard_true' or opname == 'guard_false':
                    if self.nodes[op.args[0]].const:
                        continue
                op = self.optimize_guard(op)
                newoperations.append(op)
                continue
            elif opname == 'getfield_gc':
                instnode = self.nodes[op.args[0]]
                if instnode.virtual or instnode.virtualized:
                    ofs = op.args[1].getint()
                    assert ofs in instnode.curfields    # xxx
                    self.nodes[op.results[0]] = instnode.curfields[ofs]
                    continue
            elif opname == 'new_with_vtable':
                # self.nodes[op.results[0]] keep the value from Steps (1,2)
                instnode = self.nodes[op.results[0]]
                if not instnode.escaped:
                    instnode.virtual = True
                    assert instnode.cls is not None
                    size = op.args[0].getint()
                    key = instnode.cls.source.getint()
                    type_cache.class_size[key] = size
                    continue
            elif opname == 'setfield_gc':
                instnode = self.nodes[op.args[0]]
                valuenode = self.nodes[op.args[2]]
                if instnode.virtual or instnode.virtualized:
                    ofs = op.args[1].getint()
                    instnode.curfields[ofs] = valuenode
                    continue
                assert not valuenode.virtual
            elif opname == 'ooisnull' or opname == 'oononnull':
                instnode = self.nodes[op.args[0]]
                if instnode.virtual:
                    box = op.results[0]
                    instnode = InstanceNode(box, const=True)
                    self.nodes[box] = instnode
                    continue
            elif opname == 'oois' or opname == 'ooisnot':
                instnode_x = self.nodes[op.args[0]]
                instnode_y = self.nodes[op.args[1]]
                if not instnode_x.virtual or not instnode_y.virtual:
                    box = op.results[0]
                    instnode = InstanceNode(box, const=True)
                    self.nodes[box] = instnode
                    continue
            # default handling of arguments and return value(s)
            op = self.replace_arguments(op)
            if opname in always_pure_operations:
                for box in op.args:
                    if isinstance(box, Box):
                        break
                else:
                    # all constant arguments: constant-fold away
                    for box in op.results:
                        instnode = InstanceNode(box.constbox())
                        self.nodes[box] = instnode
                    continue
            for box in op.results:
                instnode = InstanceNode(box)
                self.nodes[box] = instnode
            newoperations.append(op)

        newoperations[0].specnodes = self.specnodes
        self.loop.operations = newoperations

    def match_exactly(self, old_loop):
        old_operations = old_loop.operations
        old_mp = old_operations[0]
        assert len(old_mp.specnodes) == len(self.specnodes)
        for i in range(len(self.specnodes)):
            old_specnode = old_mp.specnodes[i]
            new_specnode = self.specnodes[i]
            if not old_specnode.equals(new_specnode):
                return False
        return True

    def match(self, old_operations):
        old_mp = old_operations[0]
        jump_op = self.loop.operations[-1]
        assert jump_op.opname == 'jump'
        assert len(old_mp.specnodes) == len(jump_op.args)
        for i in range(len(old_mp.specnodes)):
            old_specnode = old_mp.specnodes[i]
            new_instnode = self.nodes[jump_op.args[i]]
            if not old_specnode.matches(new_instnode):
                return False
        return True

    def adapt_for_match(self, old_operations):
        old_mp = old_operations[0]
        jump_op = self.loop.operations[-1]
        self.specnodes = old_mp.specnodes
        for i in range(len(old_mp.specnodes)):
            old_specnode = old_mp.specnodes[i]
            new_instnode = self.nodes[jump_op.args[i]]
            old_specnode.adapt_to(new_instnode)

def rebuild_boxes_from_guard_failure(guard_op, history, boxes_from_frame):
    allocated_boxes = []
    storage = guard_op.storage_info
    for vtable in storage.allocations:
        sizebox = ConstInt(type_cache.class_size[vtable])
        vtablebox = ConstInt(vtable)
        [instbox] = history.execute_and_record('new_with_vtable',
                                               [sizebox, vtablebox],
                                               'ptr', False)
        allocated_boxes.append(instbox)
    for index_in_alloc, ofs, index_in_arglist in storage.setfields:
        if index_in_arglist < 0:
            fieldbox = boxes_from_frame[~index_in_arglist]
        else:
            fieldbox = allocated_boxes[index_in_arglist]
        if index_in_alloc < 0:
            box = boxes_from_frame[~index_in_alloc]
        else:
            box = allocated_boxes[index_in_alloc]
        history.execute_and_record('setfield_gc',
                                   [box, ConstInt(ofs), fieldbox],
                                   'void', False)
    newboxes = []
    for index in storage.indices:
        if index < 0:
            newboxes.append(boxes_from_frame[~index])
        else:
            newboxes.append(allocated_boxes[index])
    return newboxes
