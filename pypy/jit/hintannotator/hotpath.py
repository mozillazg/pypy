from pypy.objspace.flow.model import copygraph
from pypy.translator.unsimplify import split_block
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.model import SomeLLAbstractConstant, OriginFlags


class HotPathHintAnnotator(HintAnnotator):

    def find_global_merge_point(self, graph):
        found_at = []
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'hint':
                    hints = op.args[1].value
                    if hints.get('global_merge_point'):
                        found_at.append((graph, block, op))
        if len(found_at) > 1:
            raise Exception("multiple global_merge_point not supported")
        if found_at:
            return found_at[0]
        else:
            return None

    def build_hotpath_types(self):
        # find the graph with the global_merge_point
        found_at = []
        for graph in self.base_translator.graphs:
            place = self.find_global_merge_point(graph)
            if place is not None:
                found_at.append(place)
        if len(found_at) != 1:
            raise Exception("found %d graphs with a global_merge_point,"
                            " expected 1 (for now)" % len(found_at))
        portalgraph, _, _ = found_at[0]
        # make a copy of the portalgraph before mutating it
        portalgraph = copygraph(portalgraph)
        _, portalblock, portalop = self.find_global_merge_point(portalgraph)
        portalopindex = portalblock.operations.index(portalop)
        # split the block across the global_merge_point
        link = split_block(None, portalblock, portalopindex)
        # rewire the graph to start at the global_merge_point
        portalgraph.startblock = link.target
        self.portalgraph = portalgraph
        input_args_hs = [SomeLLAbstractConstant(v.concretetype,
                                                {OriginFlags(): True})
                         for v in portalgraph.getargs()]
        return self.build_types(portalgraph, input_args_hs)
