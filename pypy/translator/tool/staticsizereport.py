from __future__ import division

from pypy.rpython.lltypesystem.lltype import typeOf, _ptr, Ptr, ContainerType
from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.memory.lltypelayout import convert_offset_to_int


def guess_module(graph):
    func = getattr(graph, 'func', None)
    name = None
    if func is not None:
        newname = func.func_globals.get('__name__',  None)
        if newname is not None:
            name = newname
        else:
            if func.__module__:
                name = func.__module__
    return name


def values_to_nodes(database, values):
    nodes = []
    for value in values:
        if isinstance(typeOf(value), Ptr) and isinstance(typeOf(value._obj), ContainerType):
            node = database.getcontainernode(value._obj)
            if node.nodekind != 'func':
                nodes.append(node)
    return nodes


def guess_size_obj(obj):
    TYPE = typeOf(obj)
    ptr = _ptr(Ptr(TYPE), obj)
    if TYPE._is_varsize():
        arrayfld = getattr(TYPE, '_arrayfld', None)
        if arrayfld:
            length = len(getattr(ptr, arrayfld))
        else:
            try:
                length = len(ptr)
            except TypeError:
                print "couldn't find size of", ptr
                return 0
    else:
        length = None
    return convert_offset_to_int(llmemory.sizeof(TYPE, length))


def guess_size(database, node, recursive=None):
    obj = node.obj
    size = guess_size_obj(obj)
    if recursive is None:
        return size
    if node in recursive:
        return 0
    recursive.add(node)
    for dep in values_to_nodes(database, node.enum_dependencies()):
        size += guess_size(database, dep, recursive)
    return size


def by_lltype(obj):
    return typeOf(obj)

def group_static_size(database, nodes, grouper=by_lltype, recursive=None):
    totalsize = {}
    numobjects = {}
    for node in nodes:
        obj = node.obj
        group = grouper(obj)
        totalsize[group] = totalsize.get(group, 0) + guess_size(database, node, recursive)
        numobjects[group] = numobjects.get(group, 0) + 1
    return totalsize, numobjects

def make_report_static_size(database, nodes, grouper, recursive=None):
    totalsize, numobjects = group_static_size(database, nodes, grouper, recursive)
    l = [(size, key) for key, size in totalsize.iteritems()]
    l.sort()
    l.reverse()
    sizesum = 0
    report = []
    for size, key in l:
        sizesum += size
        report.append((key, size, numobjects[key], size / numobjects[key]))
    return sizesum, report

def format_report_line(line):
    return str(line[0])[:50] + " " + " ".join([str(x) for x in line[1:]])


def print_report_static_size(database, grouper=by_lltype):
    " Reports all objects with a specified grouper. "
    _, report = make_report_static_size(database.globalcontainers(), grouper)
    for line in report:
        print format_report_line(line)


def get_unknown_graphs(database):
    funcnodes = [node for node in database.globalcontainers()
                     if node.nodekind == "func"]
    for node in funcnodes:
        graph = getattr(node.obj, 'graph', None)
        if not graph:
            continue
        if not guess_module(graph):
            yield graph

def print_aggregated_values_by_module_and_type(database, count_modules_separately=False):
    " Reports all objects by module and by lltype. "
    modules = {}
    reports = []
    funcnodes = [node for node in database.globalcontainers()
                     if node.nodekind == "func"]
    # extract all prebuilt nodes per module
    for node in funcnodes:
        graph = getattr(node.obj, 'graph', None)
        if not graph:
            continue
        nodes_set = modules.setdefault(guess_module(graph) or '<unknown>', set())
        assert len(node.funcgens) == 1
        nodes_set.update(values_to_nodes(database, node.funcgens[0].all_cached_consts))
    modules = modules.items()
    # make sure that gc modules are reported latest to avoid them eating all objects
    def gc_module_key(tup):
        if "module.gc" in tup[0]:
            return ("\xff", ) + tup
        return tup
    modules.sort(key=gc_module_key)

    # report sizes per module
    seen = set()
    for modulename, nodes in modules:
        if count_modules_separately:
            seen = set()
        if not nodes:
            continue
        size, report = make_report_static_size(database, nodes, by_lltype, seen)
        reports.append((size, modulename, report))
    reports.sort()
    reports.reverse()
    for size, modulename, report in reports:
        if not size:
            continue
        print "########### %i %s ####################################" % (size, modulename)
        for line in report:
            print " " * 4 + format_report_line(line)
        print

