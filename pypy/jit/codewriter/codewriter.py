from pypy.jit.codewriter import support
from pypy.jit.codewriter.regalloc import perform_register_allocation
from pypy.jit.codewriter.flatten import flatten_graph, KINDS
from pypy.jit.codewriter.assembler import Assembler, JitCode
from pypy.jit.codewriter.jitter import transform_graph
from pypy.jit.codewriter.format import format_assembler
from pypy.jit.codewriter.liveness import compute_liveness
from pypy.jit.codewriter.policy import log
from pypy.tool.udir import udir


class CodeWriter(object):

    def __init__(self, cpu=None):
        self.cpu = cpu
        self.assembler = Assembler()

    def transform_func_to_jitcode(self, func, values, type_system='lltype'):
        """For testing."""
        rtyper = support.annotate(func, values, type_system=type_system)
        graph = rtyper.annotator.translator.graphs[0]
        return self.transform_graph_to_jitcode(graph, True, True)

    def transform_graph_to_jitcode(self, graph, portal, verbose):
        """Transform a graph into a JitCode containing the same bytecode
        in a different format.  Note that the original 'graph' is mangled
        by the process and should not be used any more.
        """
        #
        # step 1: mangle the graph so that it contains the final instructions
        # that we want in the JitCode, but still as a control flow graph
        transform_graph(graph, self.cpu, portal)
        #
        # step 2a: perform register allocation on it
        regallocs = {}
        for kind in KINDS:
            regallocs[kind] = perform_register_allocation(graph, kind)
        #
        # step 2b: compute the liveness around certain operations
        compute_liveness(graph)
        #
        # step 3: flatten the graph to produce human-readable "assembler",
        # which means mostly producing a linear list of operations and
        # inserting jumps or conditional jumps.  This is a list of tuples
        # of the shape ("opname", arg1, ..., argN) or (Label(...),).
        ssarepr = flatten_graph(graph, regallocs)
        #
        # print the resulting assembler
        self.print_ssa_repr(ssarepr, portal, verbose)
        #
        # step 4: "assemble" it into a JitCode, which contains a sequence
        # of bytes and lists of constants.  It's during this step that
        # constants are cast to their normalized type (Signed, GCREF or
        # Float).
        jitcode = self.assembler.assemble(ssarepr)
        return jitcode

    def make_jitcodes(self, maingraph, verbose=False):
        self.portal_graph = maingraph
        return self.transform_graph_to_jitcode(maingraph, True, verbose)

    def print_ssa_repr(self, ssarepr, portal, verbose):
        if verbose:
            print '%s:' % (ssarepr.name,)
            print indent(format_assembler(ssarepr), 4)
        else:
            dir = udir.ensure("jitcodes", dir=1)
            if portal:
                name = "00_portal_runner"
            elif ssarepr.name and ssarepr.name != '?':
                name = ssarepr.name
            else:
                name = 'unnamed_%x' % id(ssarepr)
            dir.join(name).write(format_assembler(ssarepr))
            log.dot()


def indent(s, indent):
    indent = ' ' * indent
    return indent + s.replace('\n', '\n'+indent).rstrip(' ')
