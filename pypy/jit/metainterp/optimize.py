from pypy.rlib.objectmodel import r_dict
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp import resoperation
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

    def __init__(self, escaped, startbox=False):
        self.escaped = escaped
        self.startbox = startbox

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
        if self.escaped:  flags += 'e'
        if self.startbox: flags += 's'
        return "<InstanceNode (%s)>" % (flags,)


class PerfectSpecializationFinder(object):

    def __init__(self):
        self.nodes = {}     # Box -> InstanceNode
        self.node_escaped = InstanceNode(escaped=True)

    def clear(self):
        self.nodes.clear()

    def getnode(self, box):
        return self.nodes.get(box, self.node_escaped)

    def find_nodes(self, loop):
        self.clear()
        for box in loop.inputargs:
            self.nodes[box] = InstanceNode(escaped=False, startbox=True)
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
        self.nodes[op.result] = InstanceNode(escaped=False)

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
            fieldnode = InstanceNode(escaped=False, startbox=instnode.startbox)
            instnode.add_escape_dependency(fieldnode)
            if instnode.origfields is None:
                instnode.origfields = av_newdict()
            instnode.origfields[field] = fieldnode
        self.nodes[op.result] = fieldnode

    def find_nodes_GETFIELD_GC_PURE(self, op):
        self.find_nodes_GETFIELD_GC(op)

    def find_nodes_GUARD_CLASS(self, op):
        pass    # prevent the default handling

    def find_nodes_JUMP(self, op):
        pass    # prevent the default handling

find_nodes_ops = _findall(PerfectSpecializationFinder, 'find_nodes_')
perfect_specialization_finder = PerfectSpecializationFinder()

# ____________________________________________________________
