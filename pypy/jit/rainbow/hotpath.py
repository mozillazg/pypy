

class EntryPointsRewriter:

    def __init__(self, rtyper, hannotator, jitcode,
                 translate_support_code=True):
        self.rtyper = rtyper
        self.hannotator = hannotator
        self.jitcode = jitcode
        self.translate_support_code = translate_support_code

    def rewrite_all(self):
        for graph in self.hannotator.base_translator.graphs:
            for block in graph.iterblocks():
                for op in block.operations:
                    if op.opname == 'hint':
                        hints = op.args[1].value
                        if hints.get('can_enter_jit'):
                            index = block.operations.index(op)
                            self.rewrite_can_enter_jit(graph, block, index)

    def rewrite_can_enter_jit(self, graph, block, index):
        if graph is not self.hannotator.portalgraph:
            raise Exception("for now, can_enter_jit must be in the"
                            " same function as global_merge_point")
        # find out ./.
        
        
        if not self.translate_support_code:
            # this case is used for most tests: the jit stuff should be run
            # directly to make these tests faster
            
            portal_entry_graph_ptr = llhelper(lltype.Ptr(self.PORTAL_FUNCTYPE),
                                              self.portal_entry)
        else:
            xxx
