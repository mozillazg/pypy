import string
from pypy.rpython.ootypesystem import ootype
from pypy.translator.avm2 import types_ as types, class_ as c, record
from pypy.translator.oosupport.database import Database as OODatabase

try:
    set
except NameError:
    from sets import Set as set

class Counter(object):
    def __init__(self):
        self.counters = {}

    def inc(self, *label):
        cur = self.counters.get(label, 0)
        self.counters[label] = cur+1

    def dump(self, filename):
        f = file(filename, 'w')
        keys = self.counters.keys()
        keys.sort()
        for key in keys:
            label = ', '.join([str(item) for item in key])
            f.write('%s: %d\n' % (label, self.counters[key]))
        f.close()

class LowLevelDatabase(OODatabase):
    def __init__(self, genoo):
        OODatabase.__init__(self, genoo)
        self._pending_nodes = []
        self.classes = {} # INSTANCE --> class nodes
        self.classnames = set() # (namespace, name)
        self.functions = {} # graph --> function_name
        self.methods = {} # graph --> method_name
        self.consts = {}  # value --> AbstractConst
        self.delegates = {} # StaticMethod --> type_name
        self.recordnames = {} # RECORD --> name
        self.const_count = Counter() # store statistics about constants

    def next_count(self):
        return self.unique()

    def _default_record_name(self, RECORD):
        trans = string.maketrans('[]<>(), :', '_________')
        name = ['Record']
        # XXX: refactor this: we need a proper way to ensure unique names
        for f_name, (FIELD_TYPE, f_default) in RECORD._fields.iteritems():
            type_name = FIELD_TYPE._short_name().translate(trans)
            name.append(f_name)
            name.append(type_name)
            
        return '__'.join(name)

    def _default_class_name(self, INSTANCE):
        parts = INSTANCE._name.rsplit('.', 1)
        if len(parts) == 2:
            return parts
        else:
            return None, parts[0]

    def pending_function(self, graph, functype=None):
        if functype is None:
            function = self.genoo.Function(self, graph)
        else:
            function = functype(self, graph)
        self.pending_node(function)
        return function.get_name()

    def pending_record(self, RECORD):
        try:
            return self.recordnames[RECORD]
        except KeyError:
            pass
        name = self._default_record_name(RECORD)
        name = self.get_unique_class_name(None, name)
        self.recordnames[RECORD] = name
        r = record.Record(self, RECORD, name)
        self.pending_node(r)
        return name

    def pending_class(self, INSTANCE):
        try:
            return self.pending_node(self.classes[INSTANCE]).get_full_name()
        except KeyError:
            pass

        if 0: #isinstance(INSTANCE, runtime.NativeInstance):
            self.classes[INSTANCE] = INSTANCE._name
            return INSTANCE._name
        else:
            namespace, name = self._default_class_name(INSTANCE)
            name = self.get_unique_class_name(namespace, name)
            cls = c.Class(self, INSTANCE, namespace, name)
            self.pending_node(cls)
            self.classes[INSTANCE] = cls
            return cls.get_full_name()

    def record_function(self, graph, name):
        self.functions[graph] = name

    def graph_name(self, graph):
        # XXX: graph name are not guaranteed to be unique
        return self.functions.get(graph, None)

    def get_unique_class_name(self, namespace, name):
        base_name = name
        i = 0
        while (namespace, name) in self.classnames:
            name = '%s_%d' % (base_name, i)
            i += 1
        self.classnames.add((namespace, name))            
        return name

    def class_name(self, INSTANCE):
        if INSTANCE is ootype.ROOT:
            return "Object"
        try:
            NATIVE_INSTANCE = INSTANCE._hints['NATIVE_INSTANCE']
            return NATIVE_INSTANCE._name
        except KeyError:
            return self.classes[INSTANCE].get_full_name()
        
    ## def record_delegate(self, TYPE):
    ##     try:
    ##         return self.delegates[TYPE]
    ##     except KeyError:
    ##         name = 'StaticMethod__%d' % len(self.delegates)
    ##         self.delegates[TYPE] = name
    ##         self.pending_node(Delegate(self, TYPE, name))
    ##         return name

    def pending_node(self, node):
        """ Adds a node to the worklist, so long as it is not already there
        and has not already been rendered. """
        # assert not self.locked # sanity check
        if node in self._rendered_nodes:
            return node
        # sometimes a dependency will already
        # be there, but needs to be rendered
        # before others
        if node in self._pending_nodes:
            self._pending_nodes.remove(node)
        self._pending_nodes.append(node)
        node.dependencies()
        return node
