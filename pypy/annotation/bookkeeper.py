"""
The Bookkeeper class.
"""

from __future__ import generators
import sys, types

from pypy.objspace.flow.model import Constant
from pypy.annotation.model import SomeString, SomeChar, SomeFloat, \
     SomePtr, unionof, SomeInstance, SomeDict, SomeBuiltin, SomePBC, \
     SomeInteger, SomeExternalObject, SomeOOInstance, TLS, SomeAddress, \
     SomeUnicodeCodePoint, SomeOOStaticMeth, s_None, \
     SomeLLADTMeth, SomeBool, SomeTuple, SomeOOClass, SomeImpossibleValue, \
     SomeList, SomeObject
from pypy.annotation.classdef import ClassDef
from pypy.annotation.listdef import ListDef, MOST_GENERAL_LISTDEF
from pypy.annotation.dictdef import DictDef, MOST_GENERAL_DICTDEF
from pypy.annotation import description
from pypy.interpreter.pycode import cpython_code_signature
from pypy.interpreter.argument import Arguments, ArgErr
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython.objectmodel import r_dict
from pypy.tool.algo.unionfind import UnionFind
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.memory import lladdress

from pypy.annotation.specialize import decide_callable

class Stats:

    def __init__(self, bookkeeper):
        self.bookkeeper = bookkeeper
        self.classify = {}

    def count(self, category, *args):
        for_category = self.classify.setdefault(category, {})
        classifier = getattr(self, 'consider_%s' % category, self.consider_generic)
        outcome = classifier(*args)
        for_category[self.bookkeeper.position_key] = outcome

    def indexrepr(self, idx):
        if idx.is_constant():
            if idx.const is None:
                return ''
            if isinstance(idx, SomeInteger):
                if idx.const >=0:
                    return 'pos-constant'
                else:
                    return 'Neg-constant'
            return idx.const
        else:
            if isinstance(idx, SomeInteger):
                if idx.nonneg:
                    return "non-neg"
                else:
                    return "MAYBE-NEG"
            else:
                return self.typerepr(idx)

    def steprepr(self, stp):
        if stp.is_constant():
            if stp.const in (1, None):
                return 'step=1'
            else:
                return 'step=%s?' % stp.const
        else:
            return 'non-const-step %s' % self.typerepr(stp)

    def consider_generic(self, *args):
        return tuple([self.typerepr(x) for x in args])

    def consider_newslice(self, s_start, s_stop, s_step):
        return ':'.join([self.indexrepr(s_start), self.indexrepr(s_stop), self.steprepr(s_step)])

    def consider_list_list_eq(self, obj1, obj2):
        return obj1, obj2

    def consider_contains(self, seq):
        return seq

    def consider_non_int_eq(self, obj1, obj2):
        if obj1.knowntype == obj2.knowntype == list:
            self.count("list_list_eq", obj1, obj2)
        return obj1.knowntype.__name__, obj2.knowntype.__name__

    def consider_non_int_comp(self, obj1, obj2):
        return obj1.knowntype.__name__, obj2.knowntype.__name__

    def typerepr(self, obj):
        if isinstance(obj, SomeInstance):
            return obj.classdef.cls.__name__
        else:
            return obj.knowntype.__name__

    def consider_tuple_iter(self, tup):
        ctxt = "[%s]" % sys._getframe(4).f_code.co_name
        if tup.is_constant():
            return ctxt, tup.const
        else:
            return ctxt, tuple([self.typerepr(x) for x in tup.items])

    def consider_tuple_random_getitem(self, tup):
        return tuple([self.typerepr(x) for x in tup.items])

    def consider_list_index(self):
        return '!'

    def consider_list_getitem(self, idx):
        return self.indexrepr(idx)

    def consider_list_setitem(self, idx):
        return self.indexrepr(idx)

    def consider_list_delitem(self, idx):
        return self.indexrepr(idx)
    
    def consider_str_join(self, s):
        if s.is_constant():
            return repr(s.const)
        else:
            return "NON-CONSTANT"

    def consider_str_getitem(self, idx):
        return self.indexrepr(idx)

    def consider_strformat(self, str, args):
        if str.is_constant():
            s = repr(str.const)
        else:
            s = "?!!!!!!"
        if isinstance(args, SomeTuple):
            return (s, tuple([self.typerepr(x) for x in args.items]))
        else:
            return (s, self.typerepr(args))

    def consider_dict_getitem(self, dic):
        return dic

    def consider_dict_setitem(self, dic):
        return dic

    def consider_dict_delitem(self, dic):
        return dic
            

class Bookkeeper:
    """The log of choices that have been made while analysing the operations.
    It ensures that the same 'choice objects' will be returned if we ask
    again during reflowing.  Like ExecutionContext, there is an implicit
    Bookkeeper that can be obtained from a thread-local variable.

    Currently used for factories and user-defined classes."""

    def __setstate__(self, dic):
        self.__dict__.update(dic) # normal action
        delayed_imports()

    def __init__(self, annotator):
        self.annotator = annotator
        self.descs = {}          # map Python objects to their XxxDesc wrappers
        self.methoddescs = {}    # map (funcdesc, classdef) to the MethodDesc
        self.classdefs = []      # list of all ClassDefs
        self.cachespecializations = {}
        self.pbctypes = {}
        self.seen_mutable = {}
        self.listdefs = {}       # map position_keys to ListDefs
        self.dictdefs = {}       # map position_keys to DictDefs
        self.immutable_cache = {}

        # mapping position -> key, prev_result for specializations
        self.spec_callsite_keys_results = {}

        self.pbc_maximal_access_sets = UnionFind(description.AttrFamily)
        self.pbc_maximal_call_families = UnionFind(description.CallFamily)
        self.pbc_call_sites = {}
        self.emulated_pbc_calls = {}

        self.needs_hash_support = {}

        self.needs_generic_instantiate = {}

        self.memo_tables = []

        self.stats = Stats(self)

        delayed_imports()

    def count(self, category, *args):
        self.stats.count(category, *args)

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        self.position_key = position_key
        TLS.bookkeeper = self

    def leave(self):
        """End of an operation."""
        del TLS.bookkeeper
        del self.position_key

    def compute_at_fixpoint(self):
##        if self.pbc_maximal_call_families is None:
##            ...
##        if self.pbc_callables is None:
##            self.pbc_callables = {}

##        for (fn, block, i), shape in self.pbc_call_sites.iteritems():
##            spaceop = block.operations[i]
##            assert spaceop.opname in ('call_args', 'simple_call')
##            pbc = self.annotator.binding(spaceop.args[0], extquery=True)
##            self.consider_pbc_call(pbc, shape, spaceop)
##        self.pbc_call_sites = {}

##        for pbc, shape in self.emulated_pbc_calls.itervalues():
##            self.consider_pbc_call(pbc, shape)
##        self.emulated_pbc_calls = {}

        for cls in self.needs_hash_support.keys():
            for cls2 in self.needs_hash_support:
                if issubclass(cls, cls2) and cls is not cls2:
                    del self.needs_hash_support[cls]
                    break

    def getuniqueclassdef(self, cls):
        """Get the ClassDef associated with the given user cls.
        Avoid using this!  It breaks for classes that must be specialized.
        """
        if cls is object:
            return None
        desc = self.getdesc(cls)
        return desc.getuniqueclassdef()

    def getlistdef(self, **flags):
        """Get the ListDef associated with the current position."""
        try:
            listdef = self.listdefs[self.position_key]
        except KeyError:
            listdef = self.listdefs[self.position_key] = ListDef(self)
            listdef.listitem.__dict__.update(flags)
        return listdef

    def newlist(self, *s_values, **flags):
        """Make a SomeList associated with the current position, general
        enough to contain the s_values as items."""
        listdef = self.getlistdef(**flags)
        for s_value in s_values:
            listdef.generalize(s_value)
        return SomeList(listdef)

    def getdictdef(self):
        """Get the DictDef associated with the current position."""
        try:
            dictdef = self.dictdefs[self.position_key]
        except KeyError:
            dictdef = self.dictdefs[self.position_key] = DictDef(self)
        return dictdef

    def newdict(self, *items_s):
        """Make a SomeDict associated with the current position, general
        enough to contain the given (s_key, s_value) as items."""
        dictdef = self.getdictdef()
        for s_key, s_value in items_s:
            dictdef.generalize_key(s_key)
            dictdef.generalize_value(s_value)
        return SomeDict(dictdef)

    def immutablevalue(self, x):
        """The most precise SomeValue instance that contains the
        immutable value x."""
        # convert unbound methods to the underlying function
        if hasattr(x, 'im_self') and x.im_self is None:
            x = x.im_func
            assert not hasattr(x, 'im_self')
        if x is sys: # special case constant sys to someobject
            return SomeObject()
        tp = type(x)
        if tp is bool:
            result = SomeBool()
        elif tp is int:
            result = SomeInteger(nonneg = x>=0)
        elif tp is r_uint:
            result = SomeInteger(nonneg = True, unsigned = True)
        elif issubclass(tp, str): # py.lib uses annotated str subclasses
            if len(x) == 1:
                result = SomeChar()
            else:
                result = SomeString()
        elif tp is unicode and len(x) == 1:
            result = SomeUnicodeCodePoint()
        elif tp is tuple:
            result = SomeTuple(items = [self.immutablevalue(e) for e in x])
        elif tp is float:
            result = SomeFloat()
        elif tp is list:
            key = Constant(x)
            try:
                return self.immutable_cache[key]
            except KeyError:
                result = SomeList(ListDef(self, SomeImpossibleValue()))
                self.immutable_cache[key] = result
                for e in x:
                    result.listdef.generalize(self.immutablevalue(e))
        elif tp is dict or tp is r_dict:
            key = Constant(x)
            try:
                return self.immutable_cache[key]
            except KeyError:
                result = SomeDict(DictDef(self, 
                                          SomeImpossibleValue(),
                                          SomeImpossibleValue()))
                self.immutable_cache[key] = result
                if tp is r_dict:
                    s_eqfn = self.immutablevalue(x.key_eq)
                    s_hashfn = self.immutablevalue(x.key_hash)
                    result.dictdef.dictkey.update_rdict_annotations(s_eqfn,
                                                                    s_hashfn)
                for ek, ev in x.iteritems():
                    result.dictdef.generalize_key(self.immutablevalue(ek))
                    result.dictdef.generalize_value(self.immutablevalue(ev))
        elif ishashable(x) and x in BUILTIN_ANALYZERS:
            result = SomeBuiltin(BUILTIN_ANALYZERS[x], methodname="%s.%s" % (x.__module__, x.__name__))
        elif tp in EXTERNAL_TYPE_ANALYZERS:
            result = SomeExternalObject(tp)
        elif isinstance(x, lltype._ptr):
            result = SomePtr(lltype.typeOf(x))
        elif isinstance(x, lladdress.address):
            assert x is lladdress.NULL
            result= SomeAddress(is_null=True)
        elif isinstance(x, ootype._static_meth):
            result = SomeOOStaticMeth(ootype.typeOf(x))
        elif isinstance(x, ootype._class):
            result = SomeOOClass(x._INSTANCE)   # NB. can be None
        elif isinstance(x, ootype._instance):
            result = SomeOOInstance(ootype.typeOf(x))
        elif callable(x) or isinstance(x, staticmethod): # XXX
            if hasattr(x, '__self__') and x.__self__ is not None:
                # for cases like 'l.append' where 'l' is a global constant list
                s_self = self.immutablevalue(x.__self__)
                result = s_self.find_method(x.__name__)
                if result is None:
                    result = SomeObject()
            else:
                result = SomePBC([self.getdesc(x)])
        elif hasattr(x, '__class__') \
                 and x.__class__.__module__ != '__builtin__':
            # user-defined classes can define a method _freeze_(), which
            # is called when a prebuilt instance is found.  If the method
            # returns True, the instance is considered immutable and becomes
            # a SomePBC().  Otherwise it's just SomeInstance().
            frozen = hasattr(x, '_freeze_') and x._freeze_()
            if frozen:
                result = SomePBC([self.getdesc(x)])
            else:
                clsdef = self.getuniqueclassdef(x.__class__)
                if x not in self.seen_mutable: # avoid circular reflowing, 
                                               # see for example test_circular_mutable_getattr
                    self.seen_mutable[x] = True
                    self.event('mutable', x)
                    for attr in x.__dict__:
                        clsdef.add_source_for_attribute(attr, x) # can trigger reflowing
                result = SomeInstance(clsdef)
        elif x is None:
            return s_None
        else:
            result = SomeObject()
        result.const = x
        return result

    def getdesc(self, pyobj):
        # get the XxxDesc wrapper for the given Python object, which must be
        # one of:
        #  * a user-defined Python function
        #  * a Python type or class (but not a built-in one like 'int')
        #  * a user-defined bound or unbound method object
        #  * a frozen pre-built constant (with _freeze_() == True)
        #  * a bound method of a frozen pre-built constant
        try:
            return self.descs[pyobj]
        except KeyError:
            if isinstance(pyobj, types.FunctionType):
                result = description.FunctionDesc(self, pyobj)
            elif isinstance(pyobj, (type, types.ClassType)):
                result = description.ClassDesc(self, pyobj)
            elif isinstance(pyobj, types.MethodType):
                if pyobj.im_self is None:   # unbound
                    return self.getdesc(pyobj.im_func)
                elif (hasattr(pyobj.im_self, '_freeze_') and
                      pyobj.im_self._freeze_()):  # method of frozen
                    result = description.MethodOfFrozenDesc(self,
                        self.getdesc(pyobj.im_func),            # funcdesc
                        self.getdesc(pyobj.im_self))            # frozendesc
                else: # regular method
                    result = self.getmethoddesc(
                        self.getdesc(pyobj.im_func),            # funcdesc
                        self.getuniqueclassdef(pyobj.im_class)) # classdef
            else:
                # must be a frozen pre-built constant, but let's check
                assert pyobj._freeze_()
                result = description.FrozenDesc(self, pyobj)
                cls = result.knowntype
                if cls not in self.pbctypes:
                    self.pbctypes[cls] = True
                    # XXX what to do about this old check?:
                    #if cls in self.userclasses:
                    #    self.warning("making some PBC of type %r, which has "
                    #                 "already got a ClassDef" % (cls,))
            self.descs[pyobj] = result
            return result

    def getmethoddesc(self, funcdesc, classdef):
        try:
            return self.methoddescs[funcdesc, classdef]
        except KeyError:
            result = description.MethodDesc(self, funcdesc, classdef)
            self.methoddescs[funcdesc, classdef] = result
            return result

    def valueoftype(self, t):
        """The most precise SomeValue instance that contains all
        objects of type t."""
        assert isinstance(t, (type, types.ClassType))
        if t is bool:
            return SomeBool()
        elif t is int:
            return SomeInteger()
        elif t is r_uint:
            return SomeInteger(nonneg = True, unsigned = True)
        elif issubclass(t, str): # py.lib uses annotated str subclasses
            return SomeString()
        elif t is float:
            return SomeFloat()
        elif t is list:
            return SomeList(MOST_GENERAL_LISTDEF)
        elif t is dict:
            return SomeDict(MOST_GENERAL_DICTDEF)
        # can't do tuple
        elif t is types.NoneType:
            return s_None
        elif t in EXTERNAL_TYPE_ANALYZERS:
            return SomeExternalObject(t)
        elif t.__module__ != '__builtin__' and t not in self.pbctypes:
            classdef = self.getuniqueclassdef(t)
            return SomeInstance(classdef)
        else:
            o = SomeObject()
            if t != object:
                o.knowntype = t
            return o

    def pbc_getattr(self, pbc, s_attr):
        assert s_attr.is_constant()
        attr = s_attr.const

        descs = pbc.descriptions.keys()
        if not descs:
            return SomeImpossibleValue()
        first = descs[0]
        change = first.mergeattrfamilies(*descs[1:])
        attrfamily = first.getattrfamily()

        position = self.position_key
        attrfamily.read_locations[position] = True

        actuals = []
        for desc in attrfamily.descs:
            actuals.append(desc.s_read_attribute(attr))
        s_result = unionof(*actuals)

        attrfamily.attrs[attr] = s_result

        if change:
            for position in attrfamily.read_locations:
                self.annotator.reflowfromposition(position)
                
        return s_result

    # xxx refactor

    def consider_pbc_call(self, pbc, shape, spaceop=None, implicit_init=None): # computation done at fix-point
        if not isinstance(pbc, SomePBC):
            return
        
        if implicit_init:
            implicit_init = pbc, implicit_init
            shape = (shape[0]+1,) + shape[1:]
        else:
            implicit_init = None

        if not (spaceop is implicit_init is None):
            pbc, dontcaresc = self.query_spaceop_callable(spaceop,
                                            implicit_init=implicit_init) 

        nonnullcallables = []
        for func, classdef in pbc.prebuiltinstances.items():
            if func is None:
                continue
            if not isclassdef(classdef): 
                classdef = None

            # if class => consider __init__ too
            if isinstance(func, (type, types.ClassType)) and \
                    func.__module__ != '__builtin__':
                assert classdef is None
                init_classdef, s_init = self.get_s_init(func)
                if s_init is not None:
                    self.consider_pbc_call(s_init, shape, spaceop, implicit_init=init_classdef) 

            callable = (classdef, func)
            assert not hasattr(func, 'im_func') or func.im_self is not None
            self.pbc_callables.setdefault(func,{})[callable] = True
            nonnullcallables.append(callable)

        if nonnullcallables:
            call_families = self.pbc_maximal_call_families

            dontcare, rep, callfamily = call_families.find(nonnullcallables[0])
            for obj in nonnullcallables:
                    dontcare, rep, callfamily = call_families.union(rep, obj)

            callfamily.patterns.update({shape: True})

    def pbc_call(self, pbc, args, emulated=None):
        """Analyse a call to a SomePBC() with the given args (list of
        annotations).
        """
        descs = pbc.descriptions.keys()
        if not descs:
            return SomeImpossibleValue()
        first = descs[0]
        first.mergecallfamilies(*descs[1:])
        callfamily = first.getcallfamily()

        shape = args.rawshape()
        callfamily.patterns[shape] = True

        if emulated is None:
            whence = self.position_key
        else:
            if emulated is True:
                whence = None
            else:
                whence = emulated # callback case

        def schedule(graph, inputcells):
            return self.annotator.recursivecall(graph, whence, inputcells)

        results = []
        for desc in descs:
            results.append(desc.pycall(schedule, args))
        s_result = unionof(*results)
        return s_result

    def DISABLED_pbc_call(self, pbc, args, implicit_init=False, emulated=None):
        if not implicit_init and not emulated:
            fn, block, i = self.position_key
            assert block.operations[i].opname in ('call_args', 'simple_call')
            assert self.annotator.binding(block.operations[i].args[0], extquery=True) is pbc
            
            # extract shape from args
            shape = args.rawshape()
            if self.position_key in self.pbc_call_sites:
                assert self.pbc_call_sites[self.position_key] == shape
            else:
                self.pbc_call_sites[self.position_key] = shape

        results = []
        nonnullcallables = [(func, classdef)
                            for func, classdef in pbc.prebuiltinstances.items()
                            if func is not None]
        mono = len(nonnullcallables) == 1

        if emulated is not None:
            if emulated is True:
                context = None
            else:
                context = emulated
        else:
            context = 'current'

        for func, classdef in nonnullcallables:
            if isclassdef(classdef): 
                s_self = SomeInstance(classdef)
                args1 = args.prepend(s_self)
            else:
                args1 = args
            results.append(self.pycall(func, args1, mono, context=context))

        return unionof(*results) 

    def emulate_pbc_call(self, unique_key, pbc, args_s, replace=[], callback=None):
        args = self.build_args("simple_call", args_s)
        #shape = args.rawshape()
        #emulated_pbc_calls = self.emulated_pbc_calls
        #prev = [unique_key]
        #prev.extend(replace)
        #for other_key in prev:
        #    if other_key in emulated_pbc_calls:
        #        pbc, old_shape = emulated_pbc_calls[other_key]
        #        assert shape == old_shape
        #        del emulated_pbc_calls[other_key]
        #emulated_pbc_calls[unique_key] = pbc, shape

        if callback is None:
            emulated = True
        else:
            emulated = callback

        return self.pbc_call(pbc, args, emulated=emulated)

    # decide_callable(position, func, args, mono) -> callb, key
    # query_spaceop_callable(spaceop) -> pbc, isspecialcase
    # get_s_init(decided_cls) -> classdef, s_undecided_init

    def query_spaceop_callable(self, spaceop, implicit_init=None): # -> s_pbc, specialcase
        self.enter(None)
        try:
            if implicit_init is None:
                assert spaceop.opname in ("simple_call", "call_args")
                obj = spaceop.args[0]
                s_obj = self.annotator.binding(obj, extquery=True)
                init_classdef = None
            else:
                s_obj, init_classdef = implicit_init

            argsvars = spaceop.args[1:]
            args_s = [self.annotator.binding(v) for v in argsvars]
            args = self.build_args(spaceop.opname, args_s)

            if isinstance(s_obj, SomePBC):
                if len(s_obj.prebuiltinstances) > 1: # no specialization expected
                    return s_obj, False

                func, classdef = s_obj.prebuiltinstances.items()[0]

                if init_classdef:
                    args = args.prepend(SomeInstance(init_classdef))
                elif isclassdef(classdef): 
                    s_self = SomeInstance(classdef)
                    args = args.prepend(s_self)
            elif isinstance(s_obj, SomeLLADTMeth):
                func = s_obj.func
                args = args.prepend(SomePtr(s_obj.ll_ptrtype))
            else:
                assert False, "unexpected callable %r for query_spaceop_callable" % s_obj

            func, key = decide_callable(self, spaceop, func, args, mono=True)

            if key is None:
                return s_obj, False

            if func is None: # specialisation computes annotation direclty
                return s_obj, True

            if isinstance(s_obj, SomePBC):
                return SomePBC({func: classdef}), False
            else:
                return SomeLLADTMeth(s_obj.ll_ptrtype, func), False
        finally:
            self.leave()

    def build_args(self, op, args_s):
        space = RPythonCallsSpace()
        if op == "simple_call":
            return Arguments(space, list(args_s))
        elif op == "call_args":
            return Arguments.fromshape(space, args_s[0].const, # shape
                                       list(args_s[1:]))

    def get_s_init(self, cls):
        classdef = self.getclassdef(cls)
        init = getattr(cls, '__init__', None)
        if init is not None and init != object.__init__:
            # don't record the access of __init__ on the classdef
            # because it is not a dynamic attribute look-up, but
            # merely a static function call
            s_init = self.immutablevalue(init)
            return classdef, s_init
        else:
            return classdef, None
 
    def get_inputcells(self, func, args):
        # parse the arguments according to the function we are calling
        signature = cpython_code_signature(func.func_code)
        defs_s = []
        if func.func_defaults:
            for x in func.func_defaults:
                defs_s.append(self.immutablevalue(x))
        try:
            inputcells = args.match_signature(signature, defs_s)
        except ArgErr, e:
            raise TypeError, "signature mismatch: %s" % e.getmsg(args, func.__name__)

        return inputcells
 

    def pycall(self, func, args, mono, context='current'):
        if func is None:   # consider None as a NULL function pointer
            return SomeImpossibleValue()

        # decide and pick if necessary a specialized version
        base_func = func
        if context == 'current':
            position_key = self.position_key
        else:
            position_key = None

        # REFACTOR: the crucial point is that we don't want to pass position_key any longer to the logic in the descs
        # just args, and possibly the old annotation of the result or SomeImpossibleValue if there is none
        # see below: because of recursivecall and its needs we may have to pass a closure around recursivecall because itself it
        # wants the position_key|callback and recursivecall maybe used (but not always) by the desc logic.
        # We may be able to construct the family directly here, no more consider_pbc_call,  then we would pass/attach the shape too
        # Indeed one possibility is to have logic on the pbc to construct the familily and use that in pbc_getattr too.
        # Part of pycall logic  would go to the desc logic receiving args, etc plus helper closures related to recursivecall
        # recursivecall should also change to deal with graphs directly, getting the graph should probably be a desc task.

        func, key = decide_callable(self, position_key, func, args, mono, unpacked=True)
        
        if func is None:
            assert isinstance(key, SomeObject)
            return key

        func, args = func # method unpacking done by decide_callable
            
        if isinstance(func, (type, types.ClassType)) and \
            func.__module__ != '__builtin__':
            classdef, s_init = self.get_s_init(func)
            s_instance = SomeInstance(classdef)
            # flow into __init__() if the class has got one
            if s_init is not None:
                s_init.call(args.prepend(s_instance), implicit_init=True)
            else:
                try:
                    args.fixedunpack(0)
                except ValueError:
                    raise Exception, "no __init__ found in %r" % (classdef.cls,)
            return s_instance

        assert isinstance(func, types.FunctionType), "[%s] expected user-defined function, got %r" % (self.whereami(), func)

        inputcells = self.get_inputcells(func, args)
        if context == 'current':
            whence = self.position_key
        else:
            whence = context
        # REFACTOR: this and maybe get_inputcells should be passed as a helper closure to the descs logic
        r = self.annotator.recursivecall(func, whence, inputcells)


        # REFACTOR: how we want to deal with this? either we always mix or we get a flag/key from the logic on the descs
        # if we got different specializations keys for a same site, mix previous results for stability
        if key is not None:
            assert context == 'current'
            occurence = (base_func, self.position_key)
            try:
                prev_key, prev_r = self.spec_callsite_keys_results[occurence]
            except KeyError:
                self.spec_callsite_keys_results[occurence] = key, r
            else:
                if prev_key != key:
                    r = unionof(r, prev_r)
                    prev_key = None
                self.spec_callsite_keys_results[occurence] = prev_key, r

        return r

    def ondegenerated(self, what, s_value, where=None, called_from_graph=None):
        self.annotator.ondegenerated(what, s_value, where=where,
                                     called_from_graph=called_from_graph)
        
    def whereami(self):
        return self.annotator.whereami(self.position_key)

    def event(self, what, x):
        return self.annotator.policy.event(self, what, x)

    def warning(self, msg):
        return self.annotator.warning(msg)

def ishashable(x):
    try:
        hash(x)
    except TypeError:
        return False
    else:
        return True

# for parsing call arguments
class RPythonCallsSpace:
    """Pseudo Object Space providing almost no real operation.
    For the Arguments class: if it really needs other operations, it means
    that the call pattern is too complex for R-Python.
    """
    def newtuple(self, items_s):
        return SomeTuple(items_s)

    def newdict(self, stuff):
        raise CallPatternTooComplex, "'**' argument"

    def unpackiterable(self, s_obj, expected_length=None):
        if isinstance(s_obj, SomeTuple):
            if (expected_length is not None and
                expected_length != len(s_obj.items)):
                raise ValueError
            return s_obj.items
        raise CallPatternTooComplex, "'*' argument must be SomeTuple"

class CallPatternTooComplex(Exception):
    pass

# get current bookkeeper

def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    try:
        return TLS.bookkeeper
    except AttributeError:
        return None


def delayed_imports():
    # import ordering hack
    global BUILTIN_ANALYZERS, EXTERNAL_TYPE_ANALYZERS
    from pypy.annotation.builtin import BUILTIN_ANALYZERS
    from pypy.annotation.builtin import EXTERNAL_TYPE_ANALYZERS

