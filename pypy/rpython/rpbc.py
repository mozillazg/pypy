import types
import sys
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Void, Bool, nullptr, frozendict
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython import rclass
from pypy.rpython import robject

from pypy.rpython import callparse

class __extend__(annmodel.SomePBC):
    def rtyper_makerepr(self, rtyper):
        if self.isNone():
            return none_frozen_pbc_repr 
        kind = self.getKind()
        if issubclass(kind, description.FunctionDesc):
            if self.descriptions.keys()[0].querycallfamily():
                getRepr = FunctionsPBCRepr
            else:
                getRepr = getFrozenPBCRepr
        elif issubclass(kind, description.ClassDesc):
            # user classes
            getRepr = rtyper.type_system.rpbc.ClassesPBCRepr
            # XXX what about this?
##                 elif type(x) is type and x.__module__ in sys.builtin_module_names:
##                     # special case for built-in types, seen in faking
##                     getRepr = getPyObjRepr
        elif issubclass(kind, description.MethodDesc):
            getRepr = rtyper.type_system.rpbc.MethodsPBCRepr
        elif issubclass(kind, description.FrozenDesc):
            getRepr = getFrozenPBCRepr
        elif issubclass(kind, description.MethodOfFrozenDesc):
            getRepr = rtyper.type_system.rpbc.MethodOfFrozenPBCRepr
        else:
            raise TyperError("unexpected PBC kind %r"%(kind,))

##             elif isinstance(x, builtin_descriptor_type):
##                 # strange built-in functions, method objects, etc. from fake.py
##                 getRepr = getPyObjRepr


        return getRepr(rtyper, self)

    def rtyper_makekey(self):
        lst = list(self.descriptions)
        lst.sort()
        return tuple([self.__class__, self.can_be_None]+lst)

builtin_descriptor_type = (
    type(len),                             # type 'builtin_function_or_method'
    type(list.append),                     # type 'method_descriptor'
    type(type(None).__repr__),             # type 'wrapper_descriptor'
    type(type.__dict__['__dict__']),       # type 'getset_descriptor'
    type(type.__dict__['__basicsize__']),  # type 'member_descriptor'
    )

# ____________________________________________________________

class MultiplePBCRepr(Repr):
    """Base class for PBCReprs of multiple PBCs that can include None
    (represented as a NULL pointer)."""
    def rtype_is_true(self, hop):
        if hop.s_result.is_constant():
            assert hop.s_result.const is True    # custom __nonzero__ on PBCs?
            return hop.inputconst(Bool, hop.s_result.const)
        else:
            return hop.rtyper.type_system.check_null(self, hop)


class ConcreteCallTableRow(dict):
    """A row in a concrete call table."""

def build_concrete_calltable(rtyper, callfamily):
    """Build a complete call table of a call family
    with concrete low-level function objs.
    """
    concretetable = {}   # (shape,index): row, maybe with duplicates
    uniquerows = []      # list of rows, without duplicates
    
    def lookuprow(row):
        # a 'matching' row is one that has the same llfn, expect
        # that it may have more or less 'holes'
        for existingindex, existingrow in enumerate(uniquerows):
            for funcdesc, llfn in row.items():
                if funcdesc in existingrow:
                    if llfn != existingrow[funcdesc]:
                        break   # mismatch
            else:
                # potential match, unless the two rows have no common funcdesc
                merged = ConcreteCallTableRow(row)
                merged.update(existingrow)
                if len(merged) == len(row) + len(existingrow):
                    pass   # no common funcdesc, not a match
                else:
                    return existingindex, merged
        raise LookupError

    def addrow(row):
        # add a row to the table, potentially merging it with an existing row
        try:
            index, merged = lookuprow(row)
        except LookupError:
            uniquerows.append(row)   # new row
        else:
            if merged == uniquerows[index]:
                pass    # already exactly in the table
            else:
                del uniquerows[index]
                addrow(merged)   # add the potentially larger merged row

    concreterows = {}
    for shape, rows in callfamily.calltables.items():
        for index, row in enumerate(rows):
            concreterow = ConcreteCallTableRow()
            for funcdesc, graph in row.items():
                llfn = rtyper.getcallable(graph)
                concreterow[funcdesc] = llfn
            concreterows[shape, index] = concreterow

    for row in concreterows.values():
        addrow(row)

    for (shape, index), row in concreterows.items():
        _, biggerrow = lookuprow(row)
        concretetable[shape, index] = biggerrow

    for finalindex, row in enumerate(uniquerows):
        row.attrname = 'variant%d' % finalindex

    return concretetable, uniquerows

def get_concrete_calltable(rtyper, callfamily):
    """Get a complete call table of a call family
    with concrete low-level function objs.
    """
    # cache on the callfamily
    try:
        cached = rtyper.concrete_calltables[callfamily]
    except KeyError:
        concretetable, uniquerows = build_concrete_calltable(rtyper, callfamily)
        cached = concretetable, uniquerows, callfamily.total_calltable_size
        rtyper.concrete_calltables[callfamily] = cached
    else:
        concretetable, uniquerows, oldsize = cached
        if oldsize != callfamily.total_calltable_size:
            raise TyperError("call table was unexpectedly extended")
    return concretetable, uniquerows


class FunctionsPBCRepr(MultiplePBCRepr):
    """Representation selected for a PBC of function(s)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        self._function_signatures = None
        self.callfamily = s_pbc.descriptions.iterkeys().next().getcallfamily()
        if len(s_pbc.descriptions) == 1 and not s_pbc.can_be_None:
            # a single function
            self.lowleveltype = Void
        else:
            concretetable, uniquerows = get_concrete_calltable(self.rtyper,
                                                               self.callfamily)
            self.concretetable = concretetable
            self.uniquerows = uniquerows
            if len(uniquerows) == 1:
                row = uniquerows[0]
                examplellfn = row.itervalues().next()
                self.lowleveltype = typeOf(examplellfn)
            else:
                XXX_later

    def get_s_callable(self):
        return self.s_pbc

    def get_r_implfunc(self):
        return self, 0

    def get_signature(self):
        return self.function_signatures().itervalues().next()

    def get_args_ret_s(self):
        f, _, _ = self.get_signature()
        graph = self.rtyper.type_system_deref(f).graph
        rtyper = self.rtyper
        return [rtyper.binding(arg) for arg in graph.getargs()], rtyper.binding(graph.getreturnvar())

##    def function_signatures(self):
##        if self._function_signatures is None:
##            self._function_signatures = {}
##            for func in self.s_pbc.prebuiltinstances:
##                if func is not None:
##                    self._function_signatures[func] = getsignature(self.rtyper,
##                                                                   func)
##            assert self._function_signatures
##        return self._function_signatures

    def convert_desc(self, funcdesc):
        # get the whole "column" of the call table corresponding to this desc
        if self.lowleveltype is Void:
            return funcdesc.pyobj
        llfns = {}
        found_anything = False
        for row in self.uniquerows:
            if funcdesc in row:
                llfn = row[funcdesc]
                found_anything = True
            else:
                llfn = null
            llfns[row.attrname] = llfn
        if not found_anything:
            raise TyperError("%r not in %r" % (funcdesc,
                                               self.s_pbc.descriptions))
        if len(self.uniquerows) == 1:
            return llfn   # from the loop above
        else:
            XXX_later

    def convert_const(self, value):
        if isinstance(value, types.MethodType) and value.im_self is None:
            value = value.im_func   # unbound method -> bare function
        if self.lowleveltype is Void:
            return value
        null = nullptr(self.lowleveltype.TO)
        if value is None:
            return null
        funcdesc = self.rtyper.annotator.bookkeeper.getdesc(value)
        return self.convert_desc(funcdesc)

    def convert_to_concrete_llfn(self, v, shape, index, llop):
        """Convert the variable 'v' to a variable referring to a concrete
        low-level function.  In case the call table contains multiple rows,
        'index' and 'shape' tells which of its items we are interested in.
        """
        if self.lowleveltype is Void:
            assert len(self.s_pbc.descriptions) == 1
                                      # lowleveltype wouldn't be Void otherwise
            funcdesc, = self.s_pbc.descriptions
            row_of_one_graph = self.callfamily.calltables[shape][index]
            graph = row_of_one_graph[funcdesc]
            llfn = self.rtyper.getcallable(graph)
            return inputconst(typeOf(llfn), llfn)
        elif len(self.uniquerows) == 1:
            return v
        else:
            XXX_later

    def rtype_simple_call(self, hop):
        return self.call('simple_call', hop)

    def rtype_call_args(self, hop):
        return self.call('call_args', hop)

    def call(self, opname, hop):
        bk = self.rtyper.annotator.bookkeeper
        args = bk.build_args(opname, hop.args_s[1:])
        descs = self.s_pbc.descriptions.keys()
        shape, index = description.FunctionDesc.variant_for_call_site(bk, self.callfamily, descs, args)
        row_of_graphs = self.callfamily.calltables[shape][index]
        anygraph = row_of_graphs.itervalues().next()  # pick any witness
        vfn = hop.inputarg(self, arg=0)
        vlist = [self.convert_to_concrete_llfn(vfn, shape, index,
                                               hop.llops)]
        vlist += callparse.callparse(self.rtyper, anygraph, hop, opname)
        rresult = callparse.getrresult(self.rtyper, anygraph)
        hop.exception_is_here()
        v = hop.genop('direct_call', vlist, resulttype = rresult)
        return hop.llops.convertvar(v, rresult, hop.r_result)

class __extend__(pairtype(FunctionsPBCRepr, FunctionsPBCRepr)):
        def convert_from_to((r_fpbc1, r_fpbc2), v, llops):
            # this check makes sense because both source and dest repr are FunctionsPBCRepr
            if r_fpbc1.lowleveltype == r_fpbc2.lowleveltype:
                return v
            if r_fpbc1.lowleveltype is Void:
                return inputconst(r_fpbc2, r_fpbc1.s_pbc.const)
            return NotImplemented

def getPyObjRepr(rtyper, s_pbc):
    return robject.pyobj_repr

def getFrozenPBCRepr(rtyper, s_pbc):
    descs = s_pbc.descriptions.keys()
    assert len(descs) >= 1
    if len(descs) == 1 and not s_pbc.can_be_None:
        return SingleFrozenPBCRepr(descs[0])
    else:
        access = descs[0].queryattrfamily()
        for desc in descs[1:]:
            access1 = desc.queryattrfamily()
            assert access1 is access       # XXX not implemented
        try:
            return rtyper.pbc_reprs[access]
        except KeyError:
            result = rtyper.type_system.rpbc.MultipleFrozenPBCRepr(rtyper, descs)
            rtyper.pbc_reprs[access] = result
            rtyper.add_pendingsetup(result) 
            return result


class SingleFrozenPBCRepr(Repr):
    """Representation selected for a single non-callable pre-built constant."""
    lowleveltype = Void

    def __init__(self, frozendesc):
        self.frozendesc = frozendesc

    def rtype_getattr(_, hop):
        if not hop.s_result.is_constant():
            raise TyperError("getattr on a constant PBC returns a non-constant")
        return hop.inputconst(hop.r_result, hop.s_result.const)

# __ None ____________________________________________________
class NoneFrozenPBCRepr(SingleFrozenPBCRepr):
    
    def rtype_is_true(self, hop):
        return Constant(False, Bool)

none_frozen_pbc_repr = NoneFrozenPBCRepr(None)


class __extend__(pairtype(Repr, NoneFrozenPBCRepr)):

    def convert_from_to((r_from, _), v, llops):
        return inputconst(Void, None)
    
    def rtype_is_((robj1, rnone2), hop):
        return hop.rtyper.type_system.rpbc.rtype_is_None(robj1, rnone2, hop)

class __extend__(pairtype(NoneFrozenPBCRepr, Repr)):

    def convert_from_to((_, r_to), v, llops):
        return inputconst(r_to, None)

    def rtype_is_((rnone1, robj2), hop):
        return hop.rtyper.type_system.rpbc.rtype_is_None(
                                                robj2, rnone1, hop, pos=1)
        
class __extend__(pairtype(NoneFrozenPBCRepr, robject.PyObjRepr)):

    def convert_from_to(_, v, llops):
        return inputconst(robject.pyobj_repr, None)

# ____________________________________________________________

class AbstractClassesPBCRepr(Repr):
    """Representation selected for a PBC of class(es)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        if s_pbc.can_be_None:
            raise TyperError("unsupported: variable of type "
                             "class-pointer or None")
        if s_pbc.is_constant():
            self.lowleveltype = Void
        else:
            self.lowleveltype = rtyper.type_system.rclass.CLASSTYPE
        self._access_set = None
        self._class_repr = None

    def get_access_set(self):
        if self._access_set is None:
            access_sets = self.rtyper.annotator.getpbcaccesssets()
            classes = self.s_pbc.prebuiltinstances.keys()
            _, _, access = access_sets.find(classes[0])
            for obj in classes[1:]:
                _, _, access1 = access_sets.find(obj)
                assert access1 is access       # XXX not implemented
            commonbase = access.commonbase
            self._class_repr = rclass.getclassrepr(self.rtyper, commonbase)
            self._access_set = access
        return self._access_set

    def get_class_repr(self):
        self.get_access_set()
        return self._class_repr

    def convert_const(self, cls):
        if cls not in self.s_pbc.prebuiltinstances:
            raise TyperError("%r not in %r" % (cls, self))
        if self.lowleveltype is Void:
            return cls
        return rclass.get_type_repr(self.rtyper).convert_const(cls)

    def rtype_getattr(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        else:
            attr = hop.args_s[1].const
            vcls, vattr = hop.inputargs(self, Void)
            return self.getfield(vcls, attr, hop.llops)

    def getfield(self, vcls, attr, llops):
        access_set = self.get_access_set()
        class_repr = self.get_class_repr()
        return class_repr.getpbcfield(vcls, access_set, attr, llops)

class __extend__(pairtype(AbstractClassesPBCRepr, rclass.AbstractClassRepr)):
    def convert_from_to((r_clspbc, r_cls), v, llops):
        if r_cls.lowleveltype != r_clspbc.lowleveltype:
            return NotImplemented   # good enough for now
        return v

class __extend__(pairtype(AbstractClassesPBCRepr, AbstractClassesPBCRepr)):
    def convert_from_to((r_clspbc1, r_clspbc2), v, llops):
        # this check makes sense because both source and dest repr are ClassesPBCRepr
        if r_clspbc1.lowleveltype == r_clspbc2.lowleveltype:
            return v
        if r_clspbc1.lowleveltype is Void:
            return inputconst(r_clspbc2, r_clspbc1.s_pbc.const)
        return NotImplemented

class AbstractMethodsPBCRepr(Repr):
    """Representation selected for a PBC of the form {func: classdef...}.
    It assumes that all the methods come from the same name in a base
    classdef."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        if s_pbc.isNone():
            raise TyperError("unsupported: variable of type "
                             "bound-method-object or None")
        mdescs = s_pbc.descriptions.keys()
        methodname = mdescs[0].name
        for mdesc in mdescs[1:]:
            if mdesc.name != methodname:
                raise TyperError("cannot find a unique name under which the "
                                 "methods can be found: %r" % (
                        mdescs,))

        self.methodname = methodname
        self.classdef = mdescs[0].classdef.locate_attribute(methodname)
        # the low-level representation is just the bound 'self' argument.
        self.s_im_self = annmodel.SomeInstance(self.classdef)
        self.r_im_self = rclass.getinstancerepr(rtyper, self.classdef)
        self.lowleveltype = self.r_im_self.lowleveltype

    def convert_const(self, method):
        if getattr(method, 'im_func', None) is None:
            raise TyperError("not a bound method: %r" % method)
        return self.r_im_self.convert_const(method.im_self)

    def get_r_implfunc(self):
        r_class = self.r_im_self.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        return r_func, 1

    def get_s_callable(self):
        return self.s_pbc

    def get_method_from_instance(self, r_inst, v_inst, llops):
        # The 'self' might have to be cast to a parent class
        # (as shown for example in test_rclass/test_method_both_A_and_B)
        return llops.convertvar(v_inst, r_inst, self.r_im_self)

# ____________________________________________________________

##def getsignature(rtyper, func):
##    f = rtyper.getcallable(func)
##    graph = rtyper.type_system_deref(f).graph
##    rinputs = [rtyper.bindingrepr(v) for v in graph.getargs()]
##    if graph.getreturnvar() in rtyper.annotator.bindings:
##        rresult = rtyper.bindingrepr(graph.getreturnvar())
##    else:
##        rresult = Void
##    return f, rinputs, rresult

def samesig(funcs):
    import inspect
    argspec = inspect.getargspec(funcs[0])
    for func in funcs:
        if inspect.getargspec(func) != argspec:
            return False
    return True

# ____________________________________________________________

def commonbase(classdefs):
    result = classdefs[0]
    for cdef in classdefs[1:]:
        result = result.commonbase(cdef)
        if result is None:
            raise TyperError("no common base class in %r" % (classdefs,))
    return result

def allattributenames(classdef):
    for cdef1 in classdef.getmro():
        for attrname in cdef1.attrs:
            yield cdef1, attrname
