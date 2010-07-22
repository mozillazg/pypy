
from pypy.translator.avm2.types_ import Avm2TypeSystem
from pypy.translator.avm2.database import LowLevelDatabase
from pypy.translator.avm2.node import Node
from pypy.rpython.ootypesystem import ootype

def get_entrypoint(graph):
    from pypy.translator.avm2.test.runtest import TestEntryPoint
    try:
        ARG0 = graph.getargs()[0].concretetype
    except IndexError:
        ARG0 = None
    if isinstance(ARG0, ootype.List) and ARG0.ITEM is ootype.String:
        return StandaloneEntryPoint(graph)
    else:
        return TestEntryPoint(graph)

class BaseEntryPoint(Node):
    def create_assembler(self, gen):
        pass

    def set_db(self, db):
        self.db = db
        self.cts = Avm2TypeSystem(db)

class StandaloneEntryPoint(BaseEntryPoint):
    """
    This class produces a 'main' method that converts the argv in a
    List of Strings and pass it to the real entry point.
    """
    
    def __init__(self, graph_to_call):
        self._graph = graph_to_call

    def get_name(self):
        return 'main'

    def render(self, ilasm):
        try:
            ARG0 = self._graph.getargs()[0].concretetype
        except IndexError:
            ARG0 = None
        assert isinstance(ARG0, ootype.List) and ARG0.ITEM is ootype.String,\
               'Wrong entry point signature: List(String) expected'

        qname = self.cts.graph_to_qname(self._graph)
        ilasm.emit('findpropstrict', qname)
        ilasm.emit('callpropvoid', qname, 0)
        self.db.pending_function(self._graph)

class LibraryEntryPoint(BaseEntryPoint):
    def __init__(self, name, graphs):
        self.name = name
        self.graphs = graphs

    def get_name(self):
        return self.name

    def render(self, ilasm):
        for graph in self.graphs:
            self.db.pending_function(graph)
