from pypy.jit.codewriter import support
from pypy.jit.codewriter.regalloc import perform_register_allocation
from pypy.jit.codewriter.flatten import flatten_graph, KINDS
from pypy.jit.codewriter.assembler import Assembler
from pypy.jit.codewriter.jitter import transform_graph
from pypy.jit.codewriter.format import format_assembler


class CodeWriter(object):

    def __init__(self, cpu=None):
        self.cpu = cpu
        self.assembler = Assembler()

    def transform_func_to_jitcode(self, func, values, type_system='lltype'):
        """For testing."""
        rtyper = support.annotate(func, values, type_system=type_system)
        graph = rtyper.annotator.translator.graphs[0]
        return self.transform_graph_to_jitcode(graph)

    def transform_graph_to_jitcode(self, graph, verbose=False):
        transform_graph(graph, self.cpu)
        regallocs = {}
        for kind in KINDS:
            regallocs[kind] = perform_register_allocation(graph, kind)
        ssarepr = flatten_graph(graph, regallocs)
        if verbose:
            print graph
            print indent(format_assembler(ssarepr), 4)
        jitcode = self.assembler.assemble(ssarepr)
        return jitcode

    def make_jitcodes(self, maingraph, verbose=False):
        return self.transform_graph_to_jitcode(maingraph, verbose)


def indent(s, indent):
    indent = ' ' * indent
    return indent + s.replace('\n', '\n'+indent).rstrip(' ')
