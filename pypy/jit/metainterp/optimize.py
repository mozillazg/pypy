from pypy.rlib.objectmodel import r_dict
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.specnode import prebuiltNotSpecNode
from pypy.jit.metainterp.specnode import FixedClassSpecNode
from pypy.jit.metainterp.specnode import VirtualInstanceSpecNode
from pypy.jit.metainterp.history import AbstractValue


def av_eq(self, other):
    return self.sort_key() == other.sort_key()

def av_hash(self):
    return self.sort_key()

def av_newdict():
    return r_dict(av_eq, av_hash)

def _findall(Class, name_prefix):
    result = []
    for value, name in resoperation.opname.items():
        if hasattr(Class, name_prefix + name):
            result.append((value, getattr(Class, name_prefix + name)))
    return unrolling_iterable(result)

# ____________________________________________________________

class InstanceNode(object):
    """For the first phase: InstanceNode is used to match the start and
    the end of the loop, so it contains both 'origfields' that represents
    the field's status at the start and 'curfields' that represents it
    at the current point (== the end when the first phase is complete).
    """
    origfields = None   # optimization; equivalent to an empty dict
    curfields = None    # optimization; equivalent to an empty dict
    dependencies = None
    knownclsbox = None

    def __init__(self, escaped, fromstart=False):
        self.escaped = escaped
        self.fromstart = fromstart

    def add_escape_dependency(self, other):
        assert not self.escaped
        if self.dependencies is None:
            self.dependencies = []
        self.dependencies.append(other)

    def mark_escaped(self):
        # invariant: if escaped=True, then dependencies is None
        if not self.escaped:
            self.escaped = True
            if self.dependencies is not None:
                deps = self.dependencies
                self.dependencies = None
                for box in deps:
                    box.mark_escaped()

    def __repr__(self):
        flags = ''
        if self.escaped:     flags += 'e'
        if self.fromstart:   flags += 's'
        if self.knownclsbox: flags += 'c'
        return "<InstanceNode (%s)>" % (flags,)


class PerfectSpecializationFinder(object):
    node_escaped = InstanceNode(escaped=True)

    def __init__(self):
        self.nodes = {}     # Box -> InstanceNode

    def getnode(self, box):
        return self.nodes.get(box, self.node_escaped)

    def find_nodes(self, loop):
        inputnodes = []
        for box in loop.inputargs:
            instnode = InstanceNode(escaped=False, fromstart=True)
            inputnodes.append(instnode)
            self.nodes[box] = instnode
        self.inputnodes = inputnodes
        #
        for op in loop.operations:
            opnum = op.opnum
            for value, func in find_nodes_ops:
                if opnum == value:
                    func(self, op)
                    break
            else:
                self.find_nodes_default(op)

    def find_nodes_default(self, op):
        if not op.has_no_side_effect():
            # default case: mark the arguments as escaping
            for box in op.args:
                self.getnode(box).mark_escaped()

    def find_nodes_NEW_WITH_VTABLE(self, op):
        instnode = InstanceNode(escaped=False)
        instnode.knownclsbox = op.args[0]
        self.nodes[op.result] = instnode

    def find_nodes_SETFIELD_GC(self, op):
        instnode = self.getnode(op.args[0])
        if instnode.escaped:
            return     # nothing to be gained from tracking the field
        fieldnode = self.getnode(op.args[1])
        field = op.descr
        assert isinstance(field, AbstractValue)
        if instnode.curfields is None:
            instnode.curfields = av_newdict()
        instnode.curfields[field] = fieldnode
        instnode.add_escape_dependency(fieldnode)

    def find_nodes_GETFIELD_GC(self, op):
        instnode = self.getnode(op.args[0])
        if instnode.escaped:
            return     # nothing to be gained from tracking the field
        field = op.descr
        assert isinstance(field, AbstractValue)
        if instnode.curfields is not None and field in instnode.curfields:
            fieldnode = instnode.curfields[field]
        elif instnode.origfields is not None and field in instnode.origfields:
            fieldnode = instnode.origfields[field]
        else:
            fieldnode = InstanceNode(escaped=False,
                                     fromstart=instnode.fromstart)
            instnode.add_escape_dependency(fieldnode)
            if instnode.origfields is None:
                instnode.origfields = av_newdict()
            instnode.origfields[field] = fieldnode
        self.nodes[op.result] = fieldnode

    def find_nodes_GETFIELD_GC_PURE(self, op):
        self.find_nodes_GETFIELD_GC(op)

    def find_nodes_GUARD_CLASS(self, op):
        instbox = op.args[0]
        clsbox = op.args[1]
        try:
            instnode = self.nodes[instbox]
        except KeyError:
            instnode = self.nodes[instbox] = InstanceNode(escaped=True)
        assert instnode is not self.node_escaped
        assert (instnode.knownclsbox is None or
                instnode.knownclsbox.equals(clsbox))
        instnode.knownclsbox = clsbox

    def find_nodes_JUMP(self, op):
        """Build the list of specnodes based on the result
        computed by this PerfectSpecializationFinder.
        """
        specnodes = []
        assert len(self.inputnodes) == len(op.args)
        for i in range(len(op.args)):
            inputnode = self.inputnodes[i]
            exitnode = self.getnode(op.args[i])
            specnodes.append(self.intersect(inputnode, exitnode))
        self.specnodes = specnodes

    def intersect(self, inputnode, exitnode):
        assert inputnode.fromstart
        if exitnode.knownclsbox is None:
            return prebuiltNotSpecNode     # no known class at exit
        if (inputnode.knownclsbox is not None and
            not inputnode.knownclsbox.equals(exitnode.knownclsbox)):
            return prebuiltNotSpecNode     # mismatched known class at exit
        #
        # for the sequel, we know that the class is known and matches
        if inputnode.escaped or exitnode.escaped or exitnode.fromstart:
            if inputnode.knownclsbox is None:
                return prebuiltNotSpecNode      # class not needed at input
            return FixedClassSpecNode(exitnode.knownclsbox)
        #
        fields = []
        d = exitnode.curfields
        if d is not None:
            if inputnode.origfields is None:
                inputnode.origfields = av_newdict()
            lst = d.keys()
            sort_descrs(lst)
            for ofs in lst:
                try:
                    node = inputnode.origfields[ofs]
                except KeyError:
                    # field stored at exit, but not read at input.  Must
                    # still be allocated, otherwise it will be incorrectly
                    # uninitialized after a guard failure.
                    node = InstanceNode(escaped=False, fromstart=True)
                specnode = self.intersect(node, d[ofs])
                fields.append((ofs, specnode))
        return VirtualInstanceSpecNode(exitnode.knownclsbox, fields)

find_nodes_ops = _findall(PerfectSpecializationFinder, 'find_nodes_')

# ____________________________________________________________

def partition(array, left, right):
    last_item = array[right]
    pivot = last_item.sort_key()
    storeindex = left
    for i in range(left, right):
        if array[i].sort_key() <= pivot:
            array[i], array[storeindex] = array[storeindex], array[i]
            storeindex += 1
    # Move pivot to its final place
    array[storeindex], array[right] = last_item, array[storeindex]
    return storeindex

def quicksort(array, left, right):
    # sort array[left:right+1] (i.e. bounds included)
    if right > left:
        pivotnewindex = partition(array, left, right)
        quicksort(array, left, pivotnewindex - 1)
        quicksort(array, pivotnewindex + 1, right)

def sort_descrs(lst):
    quicksort(lst, 0, len(lst)-1)
