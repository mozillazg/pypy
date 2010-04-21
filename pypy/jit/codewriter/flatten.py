from pypy.objspace.flow.model import Variable
from pypy.jit.metainterp.history import getkind


class SSARepr(object):
    def __init__(self, name):
        self.name = name
        self.insns = []

class Label(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "Label(%r)" % (self.name, )
    def __eq__(self, other):
        return isinstance(other, Label) and other.name == self.name

class TLabel(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "TLabel(%r)" % (self.name, )
    def __eq__(self, other):
        return isinstance(other, TLabel) and other.name == self.name

class Register(object):
    def __init__(self, kind, index):
        self.kind = kind
        self.index = index

KINDS = ['int', 'ref', 'float']

# ____________________________________________________________

def flatten_graph(graph, regallocs):
    """Flatten the graph into an SSARepr, with already-computed register
    allocations.  'regallocs' in a dict {kind: RegAlloc}."""
    flattener = GraphFlattener(graph, regallocs)
    flattener.enforce_input_args()
    flattener.generate_ssa_form()
    return flattener.assembler


class GraphFlattener(object):

    def __init__(self, graph, regallocs):
        self.graph = graph
        self.regallocs = regallocs
        self.registers = {}

    def enforce_input_args(self):
        inputargs = self.graph.startblock.inputargs
        numkinds = {}
        for v in inputargs:
            kind = getkind(v.concretetype)
            if kind == 'void':
                continue
            curcol = self.regallocs[kind].getcolor(v)
            realcol = numkinds.get(kind, 0)
            numkinds[kind] = realcol + 1
            if curcol != realcol:
                assert curcol > realcol
                self.regallocs[kind].swapcolors(realcol, curcol)

    def generate_ssa_form(self):
        self.assembler = SSARepr(self.graph.name)
        self.seen_blocks = {}
        self.make_bytecode_block(self.graph.startblock)

    def make_bytecode_block(self, block):
        if block.exits == ():
            self.make_return(block.inputargs)
            return
        if block in self.seen_blocks:
            self.emitline("goto", TLabel(block))
            return
        # inserting a goto not necessary, falling through
        self.seen_blocks[block] = True
        self.emitline(Label(block))
        #
        operations = block.operations
        for i, op in enumerate(operations):
            self.serialize_op(op)
        #
        self.insert_exits(block)

    def make_return(self, args):
        if len(args) == 1:
            # return from function
            [v] = args
            kind = getkind(v.concretetype)
            if kind == 'void':
                self.emitline("void_return")
            else:
                self.emitline("%s_return" % kind, self.getcolor(args[0]))
        elif len(args) == 2:
            # exception block, raising an exception from a function
            xxx
        else:
            raise Exception("?")

    def make_link(self, link):
        if link.target.exits == ():
            self.make_return(link.args)
            return
        self.insert_renamings(link)
        self.make_bytecode_block(link.target)

    def insert_exits(self, block):
        if len(block.exits) == 1:
            link = block.exits[0]
            assert link.exitcase is None
            self.make_link(link)
        else:
            assert len(block.exits) == 2
            linkfalse, linktrue = block.exits
            if linkfalse.llexitcase == True:
                linkfalse, linktrue = linktrue, linkfalse
            #
            self.emitline('goto_if_not', TLabel(linkfalse),
                          self.getcolor(block.exitswitch))
            # true path:
            self.make_link(linktrue)
            # false path:
            self.emitline(Label(linkfalse))
            self.make_link(linkfalse)

    def optimize_goto_if_not(self, block):
        xxxxxxx
        if not self.optimize:
            raise CannotOptimize
        v = block.exitswitch
        for link in block.exits:
            if v in link.args:
                raise CannotOptimize   # variable escapes to next block
        for op in block.operations[::-1]:
            if v in op.args:
                raise CannotOptimize   # variable is also used in cur block
            if v is op.result:
                if op.opname not in ('int_lt', 'int_le', 'int_eq', 'int_ne',
                                     'int_gt', 'int_ge'):
                    raise CannotOptimize    # not a supported operation
                killop = (op.opname,) + tuple(op.args) + (v,)
                self.assembler.insns.remove(killop)
                return 'goto_if_not_' + op.opname, op.args
        raise CannotOptimize   # variable is not produced in cur block

    def insert_renamings(self, link):
        renamings = {}
        lst = [(v, self.getcolor(link.target.inputargs[i]))
               for i, v in enumerate(link.args)]
        lst.sort(key=lambda(v, w): w.index)
        for v, w in lst:
            if isinstance(v, Variable):
                v = self.getcolor(v)
                if v == w:
                    continue
            frm, to = renamings.setdefault(w.kind, ([], []))
            frm.append(v)
            to.append(w)
        for kind in KINDS:
            if kind in renamings:
                frm, to = renamings[kind]
                # If there is no cycle among the renamings, produce a series
                # of %s_copy.  Otherwise, just one %s_rename.
                result = reorder_renaming_list(frm, to)
                if result is not None:
                    for v, w in result:
                        self.emitline('%s_copy' % kind, v, w)
                else:
                    self.emitline('%s_rename' % kind, frm, to)

    def emitline(self, *line):
        self.assembler.insns.append(line)

    def serialize_op(self, op):
        args = []
        for v in op.args:
            if isinstance(v, Variable):
                v = self.getcolor(v)
            args.append(v)
        if op.result is not None:
            args.append(self.getcolor(op.result))
        self.emitline(op.opname, *args)

    def getcolor(self, v):
        kind = getkind(v.concretetype)
        col = self.regallocs[kind].getcolor(v)    # if kind=='void', fix caller
        try:
            r = self.registers[kind, col]
        except KeyError:
            r = self.registers[kind, col] = Register(kind, col)
        return r

# ____________________________________________________________

def reorder_renaming_list(frm, to):
    result = []
    pending_indices = range(len(to))
    while pending_indices:
        not_read = dict.fromkeys([frm[i] for i in pending_indices])
        still_pending_indices = []
        for i in pending_indices:
            if to[i] not in not_read:
                result.append((frm[i], to[i]))
            else:
                still_pending_indices.append(i)
        if len(pending_indices) == len(still_pending_indices):
            return None    # no progress -- there is a cycle
        pending_indices = still_pending_indices
    return result
