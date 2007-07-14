'''
reference material:
    http://webreference.com/javascript/reference/core_ref/
    http://webreference.com/programming/javascript/
    http://mochikit.com/
    http://www.mozilla.org/js/spidermonkey/
    svn co http://codespeak.net/svn/kupu/trunk/ecmaunit 
'''

import py
import os

from pypy.rpython.rmodel import inputconst
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.tool.udir import udir
from pypy.translator.flex.log import log

from pypy.translator.flex.asmgen import AsmGen
import pypy.translator.flex.asmgen as asmgen

from pypy.translator.flex.jts import JTS
from pypy.translator.flex.opcodes import opcodes
from pypy.translator.flex.function import Function
from pypy.translator.flex.database import LowLevelDatabase

from pypy.translator.oosupport.genoo import GenOO

from heapq import heappush, heappop

from StringIO import StringIO

def _path_join(root_path, *paths):
    path = root_path
    for p in paths:
        path = os.path.join(path, p)
    return path

class Tee(object):
    def __init__(self, *args):
        self.outfiles = args

    def write(self, s):
        for outfile in self.outfiles:
            outfile.write(s)

    def close(self):
        for outfile in self.outfiles:
            if outfile is not sys.stdout:
                outfile.close()

class JS(GenOO):
    TypeSystem = JTS
    opcodes = opcodes
    Function = Function
    Database = LowLevelDatabase
    
    def __init__(self, translator, functions=[], stackless=False, compress=False, \
            logging=False, use_debug=False):
        if not isinstance(functions, list):
            functions = [functions]
        GenOO.__init__(self, udir, translator, None)

        pending_graphs = [translator.annotator.bookkeeper.getdesc(f).cachedgraph(None) for f in functions ]
        for graph in pending_graphs:
            self.db.pending_function(graph)

        self.db.translator = translator
        self.use_debug = use_debug
        self.assembly_name = self.translator.graphs[0].name        
        self.tmpfile = udir.join(self.assembly_name + '.js')
    
    def gen_pendings(self):
        while self.db._pending_nodes:
            node = self.db._pending_nodes.pop()
            to_render = []
            nparent = node
            while nparent.order != 0:
                nparent = nparent.parent
                to_render.append(nparent)
            to_render.reverse()
            for i in to_render:
                i.render(self.ilasm)
            
            node.render(self.ilasm)
    
    def generate_communication_proxy(self):
        """ Render necessary stuff aroundc communication
        proxies
        """
        for proxy in self.db.proxies:
            proxy.render(self.ilasm)


    def create_assembler(self):
        out = self.tmpfile.open('w')        
        return AsmGen(out, self.assembly_name)

    def generate_source(self):
        self.ilasm = self.create_assembler()
        self.fix_names()
        self.gen_entrypoint()
        constants_code_generator = asmgen.CodeGenerator(open("py/__consts_0.as", "w"))
        constants_code_generator.write("package py ")
        constants_code_generator.openblock()
        constants_code_generator.writeline("public var __consts_0 = {};")
        constants_code_generator.closeblock()
        constants_code_generator = asmgen.CodeGenerator(open("py/__load_consts_flex.as", "w"))
        constants_code_generator.write("package py ")
        constants_code_generator.openblock()
        constants_code_generator.writeline("import flash.net.*;");
        while self.db._pending_nodes:
            self.gen_pendings()
            
            self.ilasm.push_gen( constants_code_generator )
            
            self.db.gen_constants(self.ilasm, self.db._pending_nodes)
            
            self.ilasm.pop_gen()
            
            
        self.ilasm.push_gen( constants_code_generator )
        self.ilasm.end_consts()
        const_filename = _path_join(os.path.dirname(__file__), 'jssrc', 'library.as')
        constants_code_generator.write( open(const_filename).read() )
        constants_code_generator.closeblock()
        self.ilasm.close()
        
        self.ilasm.pop_gen()        
        self.ilasm.close()
        assert len(self.ilasm.right_hand) == 0
        return self.tmpfile.strpath
        
    def write_source(self):
        
        # write down additional functions
        # FIXME: when used with browser option it should probably
        # not be used as inlined, rather another script to load
        # this is just workaround
        self.generate_source()
        sio = StringIO()
        data = self.tmpfile.open().read()

        src_filename = _path_join(os.path.dirname(__file__), 'jssrc', 'misc.as')
        flex_filename = _path_join(os.path.dirname(__file__), 'jssrc', 'flex.mxml')
        f = self.tmpfile.open("w")
        lib = open(src_filename).read()
        flex = open(flex_filename).read()
        self.ilasm = AsmGen(sio, self.assembly_name )
        self.generate_communication_proxy()
        f.write(flex%(lib, data))
        f.close()
        
        self.filename = self.tmpfile
        
        return self.tmpfile
