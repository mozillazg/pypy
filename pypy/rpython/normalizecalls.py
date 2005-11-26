import py
import types
import inspect
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import checkgraph
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.tool.sourcetools import has_varargs, valid_identifier
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import needsgc
from pypy.rpython.objectmodel import instantiate

def normalize_call_familes(annotator):
    for callfamily in annotator.bookkeeper.pbc_maximal_call_families.infos():
       normalize_calltable(annotator, callfamily)

##def normalize_function_signatures(annotator):
##    """Make sure that all functions called in a group have exactly
##    the same signature, by hacking their flow graphs if needed.
##    """
##    call_families = annotator.getpbccallfamilies()

##    # for methods, we create or complete a corresponding function-only
##    # family with call patterns that have the extra 'self' argument
##    for family in call_families.infos():
##        prevkey = None
##        for classdef, func in family.objects:
##            if classdef is not None:
##                # add (None, func) to the func_family
##                if prevkey is None:
##                    prevkey = (None, func)
##                else:
##                    call_families.union((None, func), prevkey)
##        if prevkey is not None:
##            # copy the patterns from family to func_family with the
##            # extra self argument
##            _, _, func_family = call_families.find(prevkey)
##            for pattern in family.patterns:
##                argcount = pattern[0]
##                pattern = (argcount+1,) + pattern[1:]
##                func_family.patterns[pattern] = True

##    # for bound method objects, make sure the im_func shows up too.
##    for family in call_families.infos():
##        first = family.objects.keys()[0][1]
##        for _, callable in family.objects:
##            if isinstance(callable, types.MethodType):
##                # for bound methods families for now just accept and check that
##                # they all refer to the same function
##                if not isinstance(first, types.MethodType):
##                    raise TyperError("call family with both bound methods and "
##                                     "%r" % (first,))
##                if first.im_func is not callable.im_func:
##                    raise TyperError("call family of bound methods: should all "
##                                     "refer to the same function")
##        # create a family for the common im_func
##        if isinstance(first, types.MethodType):
##            _, _, func_family = call_families.find((None, first.im_func))
##            for pattern in family.patterns:
##                argcount = pattern[0]
##                pattern = (argcount+1,) + pattern[1:]
##                func_family.patterns[pattern] = True

##    # find the most general signature of each family
##    for family in call_families.infos():
##        # collect functions in this family, ignoring:
##        #  - methods: taken care of above
##        #  - bound methods: their im_func will also show up
##        #  - classes: already handled by create_class_constructors()
##        functions = [func for classdef, func in family.objects
##                          if classdef is None and
##                not isinstance(func, (type, types.ClassType, types.MethodType))]
##        if len(functions) > 1:  # otherwise, nothing to do


def normalize_calltable(annotator, callfamily):
    """Try to normalize all rows of a table."""
    nshapes = len(callfamily.calltables)
    for shape, table in callfamily.calltables.items():
        for row in table:
            did_something = normalize_calltable_row_signature(annotator, shape,
                                                              row)
            if did_something:
                assert nshapes == 1, "XXX call table too complex"
    while True: 
        progress = False
        for shape, table in callfamily.calltables.items():
            for row in table:
                progress |= normalize_calltable_row_annotation(annotator, shape,
                                                               row)
        if not progress:
            return   # done


def normalize_calltable_row_signature(annotator, shape, row):
    graphs = row.values()
    assert graphs, "no graph??"
    sig0 = graphs[0].signature
    defaults0 = graphs[0].defaults
    for graph in graphs[1:]:
        if graph.signature != sig0:
            break
        if graph.defaults != defaults0:
            break
    else:
        return False   # nothing to do, all signatures already match
    
    shape_cnt, shape_keys, shape_star, shape_stst = shape
    assert not shape_star, "XXX not implemented"
    assert not shape_stst, "XXX not implemented"

    # for the first 'shape_cnt' arguments we need to generalize to
    # a common type
    call_nbargs = shape_cnt + len(shape_keys)

    did_something = False
    NODEFAULT = object()

    for graph in graphs:
        argnames, varargname, kwargname = graph.signature
        assert not varargname, "XXX not implemented"
        assert not kwargname, "XXX not implemented" # ?
        inputargs_s = [annotator.binding(v) for v in graph.getargs()]
        argorder = range(shape_cnt)
        for key in shape_keys:
            i = list(argnames).index(key)
            assert i not in argorder
            argorder.append(i)
        need_reordering = (argorder != range(call_nbargs))
        if need_reordering or len(graph.getargs()) != call_nbargs:
            oldblock = graph.startblock
            inlist = []
            defaults = graph.defaults or ()
            num_nondefaults = len(inputargs_s) - len(defaults)
            defaults = [NODEFAULT] * num_nondefaults + list(defaults)
            newdefaults = []
            for j in argorder:
                v = Variable(graph.getargs()[j])
                annotator.setbinding(v, inputargs_s[j])
                inlist.append(v)
                newdefaults.append(defaults[j])
            newblock = Block(inlist)
            # prepare the output args of newblock:
            # 1. collect the positional arguments
            outlist = inlist[:shape_cnt]
            # 2. add defaults and keywords
            for j in range(shape_cnt, len(inputargs_s)):
                try:
                    i = argorder.index(j)
                    v = inlist[i]
                except ValueError:
                    default = defaults[j]
                    if default is NODEFAULT:
                        raise TyperError(
                            "call pattern has %d positional arguments, "
                            "but %r takes at least %d arguments" % (
                                shape_cnt, graph.name, num_nondefaults))
                    v = Constant(default)
                outlist.append(v)
            newblock.closeblock(Link(outlist, oldblock))
            oldblock.isstartblock = False
            newblock.isstartblock = True
            graph.startblock = newblock
            for i in range(len(newdefaults)-1,-1,-1):
                if newdefaults[i] is NODEFAULT:
                    newdefaults = newdefaults[i:]
                    break
            graph.defaults = tuple(newdefaults)
            graph.signature = (tuple([argnames[j] for j in argorder]), 
                                   None, None)
            # finished
            checkgraph(graph)
            annotator.annotated[newblock] = annotator.annotated[oldblock]
            did_something = True
    return did_something

def normalize_calltable_row_annotation(annotator, shape, row):
    if len(row) <= 1:
        return False   # nothing to do
    graphs = row.values()
    
    shape_cnt, shape_keys, shape_star, shape_stst = shape
    assert not shape_star, "XXX not implemented"
    assert not shape_stst, "XXX not implemented"

    call_nbargs = shape_cnt + len(shape_keys)

    # for the first 'shape_cnt' arguments we need to generalize to
    # a common type
    graph_bindings = {}
    for graph in graphs:
        argnames, varargname, kwargname = graph.signature
        assert not varargname, "XXX not implemented"
        graph_bindings[graph] = [annotator.binding(v)
                                 for v in graph.getargs()]
        argorder = range(shape_cnt)
        for key in shape_keys:
            i = list(argnames).index(key)
            assert i not in argorder
            argorder.append(i)
        assert argorder == range(call_nbargs)

    call_nbargs = shape_cnt + len(shape_keys)
    generalizedargs = []
    for i in range(call_nbargs):
        args_s = []
        for graph, bindings in graph_bindings.items():
            args_s.append(bindings[i])
        s_value = annmodel.unionof(*args_s)
        generalizedargs.append(s_value)
    result_s = [annotator.binding(graph.getreturnvar())
                for graph in graph_bindings]
    generalizedresult = annmodel.unionof(*result_s)

    conversion = False
    for graph in graphs:
        bindings = graph_bindings[graph]
        need_conversion = (generalizedargs != bindings)
        if need_conversion:
            conversion = True
            oldblock = graph.startblock
            inlist = []
            for j, s_value in enumerate(generalizedargs):
                v = Variable(graph.getargs()[j])
                annotator.setbinding(v, s_value)
                inlist.append(v)
            newblock = Block(inlist)
            # prepare the output args of newblock and link
            outlist = inlist[:]
            newblock.closeblock(Link(outlist, oldblock))
            oldblock.isstartblock = False
            newblock.isstartblock = True
            graph.startblock = newblock
            # finished
            checkgraph(graph)
            annotator.annotated[newblock] = annotator.annotated[oldblock]
        # convert the return value too
        if annotator.binding(graph.getreturnvar()) != generalizedresult:
            conversion = True
            annotator.setbinding(graph.getreturnvar(), generalizedresult)

    return conversion


def merge_classpbc_getattr_into_classdef(rtyper):
    # code like 'some_class.attr' will record an attribute access in the
    # PBC access set of the family of classes of 'some_class'.  If the classes
    # have corresponding ClassDefs, they are not updated by the annotator.
    # We have to do it now.
    access_sets = rtyper.annotator.bookkeeper.pbc_maximal_access_sets
    for access_set in access_sets.infos():
        descs = access_set.descs
        if len(descs) <= 1:
            continue
        count = 0
        for desc in descs:
            if isinstance(desc, description.ClassDesc):
                count += 1
        if count == 0:
            continue
        if count != len(descs):
            raise TyperError("reading attributes %r: mixing instantiated "
                             "classes with something else in %r" % (
                access_set.attrs.keys(), descs.keys()))
        classdefs = [desc.getuniqueclassdef() for desc in descs]
        commonbase = classdefs[0]
        for cdef in classdefs[1:]:
            commonbase = commonbase.commonbase(cdef)
            if commonbase is None:
                raise TyperError("reading attributes %r: no common base class "
                                 "for %r" % (
                    access_set.attrs.keys(), descs.keys()))
        access_set.commonbase = commonbase
        extra_access_sets = rtyper.class_pbc_attributes.setdefault(commonbase,
                                                                   {})
        extra_access_sets[access_set] = len(extra_access_sets)

def create_class_constructors(rtyper):
    # for classes that appear in families, make a __new__ PBC attribute.
    call_families = rtyper.annotator.getpbccallfamilies()
    access_sets = rtyper.annotator.getpbcaccesssets()

    for family in call_families.infos():
        if len(family.objects) <= 1:
            continue
        count = 0
        for _, klass in family.objects:
            if isinstance(klass, (type, types.ClassType)):
                count += 1
        if count == 0:
            continue
        if count != len(family.objects):
            raise TyperError("calls to mixed class/non-class objects in the "
                             "family %r" % family.objects.keys())

        patterns = family.patterns.copy()

        klasses = [klass for (_, klass) in family.objects.keys()]
        functions = {}
        function_values = {}
        for klass in klasses:
            try:
                initfunc = klass.__init__.im_func
            except AttributeError:
                initfunc = None
            # XXX AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARGH
            #     bouh.
            if initfunc:
                args, varargs, varkw, defaults = inspect.getargspec(initfunc)
            else:
                args, varargs, varkw, defaults = ('self',), None, None, ()
            args = list(args)
            args2 = args[:]
            if defaults:
                for i in range(-len(defaults), 0):
                    args[i] += '=None'
            if varargs:
                args.append('*%s' % varargs)
                args2.append('*%s' % varargs)
            if varkw:
                args.append('**%s' % varkw)
                args2.append('**%s' % varkw)
            args.pop(0)   # 'self'
            args2.pop(0)   # 'self'
            funcsig = ', '.join(args)
            callsig = ', '.join(args2)
            klass_name = valid_identifier(klass.__name__)
            source = py.code.Source('''
                def %s__new__(%s):
                    return ____class(%s)
            ''' % (
                klass_name, funcsig, callsig))
            miniglobals = {
                '____class': klass,
                }
            exec source.compile() in miniglobals
            klass__new__ = miniglobals['%s__new__' % klass_name]
            if initfunc:
                klass__new__.func_defaults = initfunc.func_defaults
                graph = rtyper.annotator.translator.getflowgraph(initfunc)
                args_s = [rtyper.annotator.binding(v) for v in graph.getargs()]
                args_s.pop(0)   # 'self'
            else:
                args_s = []
            rtyper.annotator.build_types(klass__new__, args_s)
            functions[klass__new__] = True
            function_values[klass, '__new__'] = klass__new__

        _, _, access_set = access_sets.find(klasses[0])
        for klass in klasses[1:]:
            _, _, access_set = access_sets.union(klasses[0], klass)
        if '__new__' in access_set.attrs:
            raise TyperError("PBC access set for classes %r already contains "
                             "a __new__" % (klasses,))
        access_set.attrs['__new__'] = annmodel.SomePBC(functions)
        access_set.values.update(function_values)

        # make a call family for 'functions', copying the call family for
        # 'klasses'
        functionslist = functions.keys()
        key0 = None, functionslist[0]
        _, _, new_call_family = call_families.find(key0)
        for klass__new__ in functionslist[1:]:
            _, _, new_call_family = call_families.union(key0,
                                                        (None, klass__new__))
        new_call_family.patterns = patterns


def create_instantiate_functions(annotator):
    # build the 'instantiate() -> instance of C' functions for the vtables

    needs_generic_instantiate = annotator.bookkeeper.needs_generic_instantiate
    
    for cls, classdef in annotator.getuserclasses().items():
        if cls in needs_generic_instantiate:
            assert needsgc(classdef) # only gc-case            
            create_instantiate_function(annotator, cls, classdef)

def create_instantiate_function(annotator, cls, classdef):
    def my_instantiate():
        return instantiate(cls)
    my_instantiate = func_with_new_name(my_instantiate,
                                valid_identifier('instantiate_'+cls.__name__))
    annotator.build_types(my_instantiate, [])
    # force the result to be converted to a generic OBJECTPTR
    generalizedresult = annmodel.SomeInstance(classdef=None)
    graph = annotator.translator.getflowgraph(my_instantiate)
    annotator.setbinding(graph.getreturnvar(), generalizedresult)
    classdef.my_instantiate = my_instantiate

def assign_inheritance_ids(annotator):
    def assign_id(classdef, nextid):
        classdef.minid = nextid
        nextid += 1
        for subclass in classdef.subdefs:
            nextid = assign_id(subclass, nextid)
        classdef.maxid = nextid
        return classdef.maxid
    id_ = 0
    for classdef in annotator.bookkeeper.classdefs:
        if classdef.basedef is None:
            id_ = assign_id(classdef, id_)
        
def perform_normalizations(rtyper):
    #XXX later: create_class_constructors(rtyper)
    rtyper.annotator.frozen += 1
    try:
        normalize_call_familes(rtyper.annotator)
        #XXX later: normalize_function_signatures(rtyper.annotator)
        #XXX later: specialize_pbcs_by_memotables(rtyper.annotator) 
        merge_classpbc_getattr_into_classdef(rtyper)
        assign_inheritance_ids(rtyper.annotator)
    finally:
        rtyper.annotator.frozen -= 1
    #XXX later: create_instantiate_functions(rtyper.annotator)
