from pypy.objspace.flow.model import checkgraph, copygraph
from pypy.translator.unsimplify import split_block
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags


class HotPathHintAnnotator(HintAnnotator):

    def find_jit_merge_point(self, graph):
        found_at = []
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'jit_merge_point':
                    found_at.append((graph, block, op))
        if len(found_at) > 1:
            raise Exception("multiple jit_merge_point() not supported")
        if found_at:
            return found_at[0]
        else:
            return None

    def build_hotpath_types(self):
        self.prepare_portal_graphs()
        input_args_hs = [SomeLLAbstractConstant(v.concretetype,
                                                {OriginFlags(): True})
                         for v in self.portalgraph.getargs()]
        return self.build_types(self.portalgraph, input_args_hs)

    def prepare_portal_graphs(self):
        # find the graph with the jit_merge_point()
        found_at = []
        for graph in self.base_translator.graphs:
            place = self.find_jit_merge_point(graph)
            if place is not None:
                found_at.append(place)
        if len(found_at) != 1:
            raise Exception("found %d graphs with a jit_merge_point(),"
                            " expected 1 (for now)" % len(found_at))
        origportalgraph, _, _ = found_at[0]
        #
        # We make a copy of origportalgraph and mutate it to make it
        # the portal.  The portal really starts at the jit_merge_point()
        # without any block or operation before it.
        #
        portalgraph = copygraph(origportalgraph)
        _, portalblock, portalop = self.find_jit_merge_point(portalgraph)
        portalopindex = portalblock.operations.index(portalop)
        # split the block just before the jit_merge_point()
        link = split_block(None, portalblock, portalopindex)
        # split again, this time enforcing the order of the live vars
        # specified by the user in the jit_merge_point() call
        _, portalblock, portalop = self.find_jit_merge_point(portalgraph)
        assert portalop is portalblock.operations[0]
        livevars = portalop.args[2:]
        link = split_block(None, portalblock, 0, livevars)
        # rewire the graph to start at the global_merge_point
        portalgraph.startblock.isstartblock = False
        portalgraph.startblock = link.target
        portalgraph.startblock.isstartblock = True
        self.portalgraph = portalgraph
        # check the new graph: errors mean some live vars have not
        # been listed in the jit_merge_point()
        checkgraph(portalgraph)
