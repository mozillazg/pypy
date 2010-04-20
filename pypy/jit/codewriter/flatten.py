from pypy.objspace.flow.model import Variable


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
    def __init__(self, index):
        self.index = index

# ____________________________________________________________

def flatten_graph(graph, regalloc):
    """Flatten the graph into an SSARepr, with already-computed register
    allocations."""
    flattener = GraphFlattener(graph, regalloc)
    flattener.enforce_input_args()
    flattener.generate_ssa_form()
    return flattener.assembler


class GraphFlattener(object):

    def __init__(self, graph, regalloc):
        self.graph = graph
        self.regalloc = regalloc
        self.registers = {}

    def enforce_input_args(self):
        inputargs = self.graph.startblock.inputargs
        for i in range(len(inputargs)):
            col = self.regalloc.getcolor(inputargs[i])
            if col != i:
                assert col > i
                self.regalloc.swapcolors(i, col)
        for i in range(len(inputargs)):
            assert self.regalloc.getcolor(inputargs[i]) == i

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
            self.emitline("int_return", self.getcolor(args[0]))
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
        renamings_from = []
        renamings_to = []
        lst = [(v, self.getcolor(link.target.inputargs[i]))
               for i, v in enumerate(link.args)]
        lst.sort(key=lambda(v, w): w.index)
        for v, w in lst:
            if isinstance(v, Variable):
                v = self.getcolor(v)
                if v == w:
                    continue
            renamings_from.append(v)
            renamings_to.append(w)
        if renamings_from:
            self.emitline('int_rename', renamings_from, renamings_to)

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
        col = self.regalloc.getcolor(v)
        try:
            r = self.registers[col]
        except KeyError:
            r = self.registers[col] = Register(col)
        return r
