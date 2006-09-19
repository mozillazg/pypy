from pypy.objspace.flow     import model as flowmodel
from pypy.annotation        import model as annmodel
from pypy.jit.hintannotator import model as hintmodel
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rmodel import inputconst
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.translator.unsimplify import split_block, split_block_at_start


class HintGraphTransformer(object):

    def __init__(self, hannotator, graph):
        self.hannotator = hannotator
        self.graph = graph
        self.dispatch_to = []
        self.latestexitindex = -1

    def transform(self):
        self.insert_enter_graph()
        self.insert_leave_graph()

    # __________ helpers __________

    def genop(self, llops, opname, args, result_type=None):
        # 'result_type' can be a LowLevelType (for green returns)
        # or a template variable whose hintannotation is copied
        if result_type is None:
            v_res = self.new_void_var()
        elif isinstance(result_type, lltype.LowLevelType):
            v_res = varoftype(result_type)
            hs = hintmodel.SomeLLAbstractConstant(result_type, {})
            self.hannotator.setbinding(v_res, hs)
        elif isinstance(result_type, flowmodel.Variable):
            var = result_type
            v_res = copyvar(self.hannotator, var)
        else:
            raise TypeError("result_type=%r" % (result_type,))

        spaceop = flowmodel.SpaceOperation(opname, args, v_res)
        llops.append(spaceop)
        return v_res

    def new_void_var(self, name=None):
        v_res = varoftype(lltype.Void, name)
        self.hannotator.setbinding(v_res, annmodel.s_ImpossibleValue)
        return v_res

    def new_block_before(self, block):
        newinputargs = [copyvar(self.hannotator, var)
                        for var in block.inputargs]
        newblock = flowmodel.Block(newinputargs)
        bridge = flowmodel.Link(newinputargs, block)
        newblock.closeblock(bridge)
        return newblock

    # __________ transformation steps __________

    def insert_enter_graph(self):
        entryblock = self.new_block_before(self.graph.startblock)
        entryblock.isstartblock = True
        self.graph.startblock.isstartblock = False
        self.graph.startblock = entryblock

        self.genop(entryblock.operations, 'enter_graph', [])

    def insert_leave_graph(self):
        block = self.graph.returnblock
        [v_retbox] = block.inputargs
        block.operations = []
        split_block(self.hannotator, block, 0)
        [link] = block.exits
        assert len(link.args) == 0
        link.args = [inputconst(lltype.Void, None)]
        link.target.inputargs = [self.new_void_var('dummy')]
        self.graph.returnblock = link.target
        self.graph.returnblock.operations = ()

        self.genop(block.operations, 'save_locals', [v_retbox])
        self.genop(block.operations, 'leave_graph', [])
