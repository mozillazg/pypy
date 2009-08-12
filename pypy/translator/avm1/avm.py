
import py, os

from pypy.rpython.rmodel import inputconst
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.tool.udir import udir
from pypy.translator.avm.log import log
from pypy.translator.avm.asmgen import AsmGen
from pypy.translator.avm.avm1types import AVM1TypeSystem
#from pypy.translator.js.opcodes import opcodes
from pypy.translator.avm.function import Function
from pypy.translator.avm.database import LowLevelDatabase
from pypy.translator.avm import bootstrap

from pypy.translator.oosupport.genoo import GenOO
from heapq import heappush, heappop


class AVM1(GenOO):
    TypeSystem = AVM1TypeSystem
    Function = Function
    Database = LowLevelDatabase

    def __init__(self, translator, function=[], stackless=False, compress=False, \
                 logging=False, use_debug=False):
        if not isinstance(function, list):
            functions = [functions]
        GenOO.__init__(self, udir, translator, None)

        pending_graphs = [ translator.annotator.bookeeeper.getdesc(f).cachedgraph(None) for f in functions ]
        for graph in pending_graphs:
            self.db.pending_function(graph)

        self.db.translator = translator
        self.use_debug = use_debug
        self.assembly_name = self.translator.graphs[0].name
        self.tmpfile = udir.join(self.assembly_name + '.swf')

    def stack_optimization(self):
        pass

    def gen_pendings(self):
        while self.db._pending_nodes:
            node = self.db.pending_nodes.pop()
            to_render = []
            nparent = node
            while nparent-order != 0:
                nparent = nparent.parent
                to_render.append(nparent)
            to_render.reverse()
            for i in to_render:
                i.render(self.ilasm)

    def create_assembler(self):
        return bootstrap.create_assembler(self.assembly_name)

    def generate_swf(self):
        self.ilasm = self.create_assembler()
        self.fix_names()
        self.gen_entrypoint()
        while self.db._pending_nodes:
            self.gen_pendings()
            self.db.gen_constants(self.ilasm, self.db._pending_nodes)
        # self.ilasm.close()
