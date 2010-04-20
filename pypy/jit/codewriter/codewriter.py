from pypy.jit.codewriter import support
from pypy.jit.codewriter.regalloc import perform_register_allocation
from pypy.jit.codewriter.flatten import flatten_graph, KINDS
from pypy.jit.codewriter.assembler import Assembler


class CodeWriter(object):

    def __init__(self):
        self.assembler = Assembler()

    def transform_func_to_jitcode(self, func, values, type_system='lltype'):
        """For testing."""
        rtyper = support.annotate(func, values, type_system=type_system)
        graph = rtyper.annotator.translator.graphs[0]
        return self.transform_graph_to_jitcode(graph)

    def transform_graph_to_jitcode(self, graph):
        regallocs = {}
        for kind in KINDS:
            regallocs[kind] = perform_register_allocation(graph, kind)
        ssarepr = flatten_graph(graph, regallocs)
        jitcode = self.assembler.assemble(ssarepr)
        return jitcode
