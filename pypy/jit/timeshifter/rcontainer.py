import operator
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import cachedtype, cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import base_ptr_lltype, cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.timeshifter import rvalue, rvirtualizable
from pypy.jit.rainbow.typesystem import deref, fieldType
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated

from pypy.annotation import model as annmodel

from pypy.rpython.lltypesystem import lloperation
debug_print = lloperation.llop.debug_print
debug_pdb = lloperation.llop.debug_pdb

class SegfaultException(Exception):
    "Signals a run-time segfault detected at compile-time."


class AbstractContainer(object):
    _attrs_ = []

    def op_getfield(self, jitstate, fielddesc):
        raise NotImplementedError

    def op_setfield(self, jitstate, fielddesc, valuebox):
        raise NotImplementedError

    def op_getsubstruct(self, jitstate, fielddesc):
        raise NotImplementedError


class VirtualContainer(AbstractContainer):
    _attrs_ = ('ownbox',)

    allowed_in_virtualizable = False

    def setforced(self, _):
        raise NotImplementedError

    def op_ptreq(self, jitstate, otherbox, reverse):
        equal = self is otherbox.content
        return rvalue.ll_fromvalue(jitstate, equal ^ reverse)


class FrozenContainer(AbstractContainer):
    _attrs_ = []

    def exactmatch(self, vstruct, outgoingvarboxes, memo):
        raise NotImplementedError
    
    def unfreeze(self, incomingvarboxes, memo):
        raise NotImplementedError

# ____________________________________________________________

class AbstractStructTypeDesc(object):
    __metaclass__ = cachedtype

    VirtualStructCls = None # patched later with VirtualStruct

    _attrs_ =  """TYPE PTRTYPE name
                    firstsubstructdesc arrayfielddesc
                    innermostdesc
                    ptrkind
                    alloctoken varsizealloctoken
                    null gv_null
                    fielddescs fielddesc_by_name
                    immutable noidentity
                    materialize
                    devirtualize
                    allocate populate
                    allocate_varsize
                 """.split()
                            

    firstsubstructdesc = None
    materialize = None
    StructFieldDesc = None

    def __init__(self, RGenOp, TYPE):
        self.TYPE = TYPE
        self.PTRTYPE = self.Ptr(TYPE)
        self.name = self._get_type_name(TYPE)
        self.ptrkind = RGenOp.kindToken(self.PTRTYPE)

        hints = getattr(TYPE, '_hints', {})
        self.immutable = hints.get('immutable', False)
        self.noidentity = hints.get('noidentity', False)

        fixsize = not TYPE._is_varsize()

        if fixsize:
            self.alloctoken = RGenOp.allocToken(TYPE)
            
        self.null = self.PTRTYPE._defl()
        self.gv_null = RGenOp.constPrebuiltGlobal(self.null)

        self._compute_fielddescs(RGenOp)
        self._define_helpers(TYPE, fixsize)


    def Ptr(self, TYPE):
        raise NotImplementedError

    def _define_helpers(self, TYPE, fixsize):
        raise NotImplementedError

    def _iter_fields(self, TYPE):
        for name in TYPE._names:
            FIELDTYPE = getattr(TYPE, name)
            yield name, FIELDTYPE

    def _get_type_name(self, TYPE):
        return TYPE._name

    def _compute_fielddescs(self, RGenOp):
        TYPE = self.TYPE
        innermostdesc = self
        fielddescs = []
        fielddesc_by_name = {}
        for name, FIELDTYPE in self._iter_fields(TYPE):
            if isinstance(FIELDTYPE, lltype.ContainerType):
                if isinstance(FIELDTYPE, lltype.Array):
                    self.arrayfielddesc = ArrayFieldDesc(RGenOp, FIELDTYPE)
                    self.varsizealloctoken = RGenOp.varsizeAllocToken(TYPE)
                    continue
                substructdesc = StructTypeDesc(RGenOp, FIELDTYPE)
                assert name == TYPE._names[0], (
                    "unsupported: inlined substructures not as first field")
                fielddescs.extend(substructdesc.fielddescs)
                self.firstsubstructdesc = substructdesc
                innermostdesc = substructdesc.innermostdesc
            else:
                index = len(fielddescs)
                if FIELDTYPE is lltype.Void:
                    desc = None
                else:
                    desc = self.StructFieldDesc(RGenOp, self.PTRTYPE, name, index)
                    fielddescs.append(desc)
                fielddesc_by_name[name] = desc

        self.fielddescs = fielddescs
        self.fielddesc_by_name = fielddesc_by_name
        self.innermostdesc = innermostdesc

    def _define_allocate(self, fixsize):
        TYPE = self.TYPE
        descs = unrolling_iterable(self.fielddescs)

        if fixsize:
            def allocate(rgenop):
                s = lltype.malloc(TYPE)
                return rgenop.genconst(s)
            self.allocate = allocate
        else:
            def allocate_varsize(rgenop, size):
                s = lltype.malloc(TYPE, size)
                return rgenop.genconst(s)
            self.allocate_varsize = allocate_varsize

        def populate(content_boxes, gv_s, box_gv_reader):
            s = gv_s.revealconst(lltype.Ptr(TYPE))
            for desc in descs:
                box = content_boxes[desc.fieldindex]
                gv_value = box_gv_reader(box)
                FIELDTYPE = getattr(desc.PTRTYPE.TO, desc.fieldname)
                v = gv_value.revealconst(FIELDTYPE)
                tgt = lltype.cast_pointer(desc.PTRTYPE, s)
                setattr(tgt, desc.fieldname, v)
        self.populate = populate

    def _define_devirtualize(self):
        TYPE = self.TYPE
        PTRTYPE = self.PTRTYPE
        descs = unrolling_iterable(self.fielddescs)

        def make(vrti):
            s = lltype.malloc(TYPE)
            s = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            return s
        
        def fill_into(vablerti, s, base, vrti):
            s = lltype.cast_opaque_ptr(PTRTYPE, s)
            i = 0
            for desc in descs:
                v = vrti._read_field(vablerti, desc, base, i)
                tgt = lltype.cast_pointer(desc.PTRTYPE, s)
                setattr(tgt, desc.fieldname, v)
                i = i + 1

        self.devirtualize = make, fill_into

    def _define_materialize(self):
        TYPE = self.TYPE
        descs = unrolling_iterable(self.fielddescs)
        
        def materialize(rgenop, boxes):
            s = lltype.malloc(TYPE)
            i = 0
            for desc in descs:
                v = rvalue.ll_getvalue(boxes[i], desc.RESTYPE)
                tgt = lltype.cast_pointer(desc.PTRTYPE, s)
                setattr(tgt, desc.fieldname, v)
                i = i + 1
            return rgenop.genconst(s)

        self.materialize = materialize
        
    def getfielddesc(self, name):
        try:
            return self.fielddesc_by_name[name]
        except KeyError:
            return self.firstsubstructdesc.getfielddesc(name)


    def factory(self):
        vstruct = self.VirtualStructCls(self)
        vstruct.content_boxes = [desc.makedefaultbox()
                                 for desc in self.fielddescs]
        box = rvalue.PtrRedBox(known_nonzero=True)
        box.content = vstruct
        vstruct.ownbox = box
        return box


class StructTypeDesc(AbstractStructTypeDesc):
    
    StructFieldDesc = None # patched later with StructFieldDesc

    _attrs_ = []

    def __new__(cls, RGenOp, TYPE):
        if TYPE._hints.get('virtualizable', False):
            return object.__new__(VirtualizableStructTypeDesc)
        else:
            return object.__new__(StructTypeDesc)

    def Ptr(self, TYPE):
        return lltype.Ptr(TYPE)

    def _define_helpers(self, TYPE, fixsize):
        if TYPE._gckind == 'gc':    # no 'allocate' for inlined substructs
            if self.immutable and self.noidentity:
                self._define_materialize()
            if fixsize:
                self._define_devirtualize()
            self._define_allocate(fixsize)


class InstanceTypeDesc(AbstractStructTypeDesc):

    StructFieldDesc = None # patched later with InstanceFieldDesc

    def Ptr(self, TYPE):
        return TYPE

    def _define_helpers(self, TYPE, fixsize):
        pass

    def _iter_fields(self, TYPE):
        try:
            fields = TYPE._fields
        except AttributeError:
            return
        for name, (FIELDTYPE, defl) in fields.iteritems():
            yield name, FIELDTYPE

    def _get_type_name(self, TYPE):
        try:
            return TYPE._name
        except AttributeError:
            return TYPE._short_name()

    def _compute_fielddescs(self, RGenOp):
        AbstractStructTypeDesc._compute_fielddescs(self, RGenOp)
        TYPE = self.TYPE
        if isinstance(TYPE, ootype.Instance):
            SUPERTYPE = TYPE._superclass
            if SUPERTYPE is not None:
                desc = InstanceTypeDesc(RGenOp, SUPERTYPE)
                self.fielddescs = desc.fielddescs + self.fielddescs
                self.fielddesc_by_name.update(desc.fielddesc_by_name)

def create_varsize(jitstate, contdesc, sizebox):
    gv_size = sizebox.getgenvar(jitstate)
    alloctoken = contdesc.varsizealloctoken
    genvar = jitstate.curbuilder.genop_malloc_varsize(alloctoken, gv_size)
    # XXX MemoryError checking
    return rvalue.PtrRedBox(genvar, known_nonzero=True)


class VirtualizableStructTypeDesc(StructTypeDesc):

    VirtualStructCls = None # patched later with VirtualizableStruct

    _attrs_  =  """redirected_fielddescs
                   redirected
                   base_desc rti_desc access_desc
                   get_gv_access
                   touch_update
                   get_gv_access_is_null access_is_null_token
                   get_rti set_rti
                """.split()

    def __init__(self, RGenOp, TYPE):
        StructTypeDesc.__init__(self, RGenOp, TYPE)
        ACCESS = self.TYPE.ACCESS
        redirected_fields = ACCESS.redirected_fields
        self.redirected_fielddescs = []
        self.redirected = {}
        i = 0
        for fielddesc in self.fielddescs:
            if fielddesc.fieldname in redirected_fields:
                self.redirected_fielddescs.append((fielddesc, i))
                self.redirected[i] = None
            i += 1
        self.base_desc = self.getfielddesc('vable_base')
        self.rti_desc = self.getfielddesc('vable_rti')
        self.access_desc = self.getfielddesc('vable_access')
        TOPPTR = self.access_desc.PTRTYPE
        self.STRUCTTYPE = TOPPTR
        self.s_structtype = annmodel.lltype_to_annotation(TOPPTR)

        firstsubstructdesc = self.firstsubstructdesc
        if (firstsubstructdesc is not None and 
            isinstance(firstsubstructdesc, VirtualizableStructTypeDesc)):
            p_untouched = firstsubstructdesc.my_redirected_getsetters_untouched
            p_touched = firstsubstructdesc.my_redirected_getsetters_touched
        else:
            p_untouched = None
            p_touched = None
        gs_untouched = rvirtualizable.GetSetters(ACCESS, p_untouched)
        gs_touched = rvirtualizable.GetSetters(ACCESS, p_untouched)
        self.get_gv_access = gs_untouched.get_gv_access

        self.my_redirected_getsetters_untouched = gs_untouched
        self.my_redirected_getsetters_touched = gs_touched
        self.my_redirected_names = my_redirected_names = []
        j = -1
        for fielddesc, _  in self.redirected_fielddescs:
            j += 1
            if fielddesc.PTRTYPE != self.PTRTYPE:
                continue
            my_redirected_names.append(fielddesc.fieldname)
            self._define_getset_field_ptr(RGenOp, fielddesc, j)

        self.touch_update = rvirtualizable.define_touch_update(TOPPTR,
                                self.redirected_fielddescs,
                                gs_touched.get_access)

        self._define_collect_residual_args()

        self._define_access_is_null(RGenOp)

    def _define_virtual_desc(self):
        pass

    def _define_getset_field_ptr(self, RGenOp, fielddesc, j):
        untouched = self.my_redirected_getsetters_untouched
        touched = self.my_redirected_getsetters_touched

        fnpairs = rvirtualizable.define_getset_field_ptrs(fielddesc, j)

        name = fielddesc.fieldname
        for getsetters, (get_field, set_field) in zip((untouched, touched),
                                                      fnpairs):
            getsetters.define('get_' + name, get_field)
            getsetters.define('set_' + name, set_field)

    def _define_collect_residual_args(self):
        my_redirected_names = unrolling_iterable(self.my_redirected_names)
        TOPPTR = self.access_desc.PTRTYPE

        if TOPPTR == self.PTRTYPE:
            _super_collect = None
        else:
            _super_collect = self.firstsubstructdesc._collect_residual_args

        def _collect_residual_args(v): 
            if _super_collect is None:
                assert not v.vable_access  # xxx need to use access ?
                t = ()
            else:
                t = _super_collect(v.super)
            for name in my_redirected_names:
                t = t + (getattr(v, name),)
            return t

        self._collect_residual_args = _collect_residual_args

        def collect_residual_args(v): 
            t = (v,) + _collect_residual_args(v)
            return t

        self.collect_residual_args = collect_residual_args


    def _define_access_is_null(self, RGenOp):
        def access_is_null(struc):
            assert not struc.vable_access
        TYPE = lltype.Ptr(lltype.FuncType([self.STRUCTTYPE], lltype.Void))
        def get_gv_access_is_null(builder):
            access_is_null_ptr = llhelper(TYPE, access_is_null)
            return builder.rgenop.genconst(access_is_null_ptr)
        self.get_gv_access_is_null = get_gv_access_is_null
        self.access_is_null_token = RGenOp.sigToken(TYPE.TO)

    def factory(self):
        vstructbox = StructTypeDesc.factory(self)
        outsidebox = rvalue.PtrRedBox(self.gv_null)
        content = vstructbox.content
        assert isinstance(content, VirtualizableStruct)
        content.content_boxes.append(outsidebox)             
        return vstructbox


class InteriorDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, RGenOp, TOPCONTAINER, path):
        self.TOPCONTAINER = TOPCONTAINER
        self.path = path
        PTRTYPE = lltype.Ptr(TOPCONTAINER)
        TYPE = TOPCONTAINER
        fielddescs = []
        for offset in path:
            LASTCONTAINER = TYPE
            if offset is None:           # array substruct
                fielddescs.append(ArrayFieldDesc(RGenOp, TYPE))
                TYPE = TYPE.OF
            else:
                fielddescs.append(NamedFieldDesc(RGenOp, lltype.Ptr(TYPE),
                                                 offset))
                TYPE = getattr(TYPE, offset)
        unroll_path = unrolling_iterable(path)
        self.VALUETYPE = TYPE

        if not isinstance(TYPE, lltype.ContainerType):
            lastoffset = path[-1]
            lastfielddesc = fielddescs[-1]
            immutable = LASTCONTAINER._hints.get('immutable', False)
            perform_getinterior_initial, gengetinterior_initial = \
                    make_interior_getter(fielddescs[:-1])

            def perform_getinteriorfield(rgenop, genvar, indexes_gv):
                ptr = perform_getinterior_initial(rgenop, genvar, indexes_gv)
                if lastoffset is None:      # getarrayitem
                    lastindex = indexes_gv[-1].revealconst(lltype.Signed)
                    result = ptr[lastindex]
                else:  # getfield
                    result = getattr(ptr, lastfielddesc.fieldname)
                return rgenop.genconst(result)

            def perform_setinteriorfield(rgenop, genvar, indexes_gv,
                                         gv_newvalue):
                ptr = perform_getinterior_initial(rgenop, genvar, indexes_gv)
                newvalue = gv_newvalue.revealconst(TYPE)
                if lastoffset is None:      # setarrayitem
                    lastindex = indexes_gv[-1].revealconst(lltype.Signed)
                    ptr[lastindex] = newvalue
                else:  # setfield
                    setattr(ptr, lastfielddesc.fieldname, newvalue)

            def gengetinteriorfield(jitstate, deepfrozen, argbox, indexboxes):
                if (immutable or deepfrozen) and argbox.is_constant():
                    # try to constant-fold
                    indexes_gv = unbox_indexes(jitstate, indexboxes)
                    if indexes_gv is not None:
                        try:
                            gv_res = perform_getinteriorfield(
                                jitstate.curbuilder.rgenop,
                                argbox.getgenvar(jitstate),
                                indexes_gv)
                        except SegfaultException:
                            pass
                        else:
                            # constant-folding: success
                            return lastfielddesc.makebox(jitstate, gv_res)

                argbox = gengetinterior_initial(jitstate, argbox, indexboxes)
                if lastoffset is None:      # getarrayitem
                    indexbox = indexboxes[-1]
                    genvar = jitstate.curbuilder.genop_getarrayitem(
                        lastfielddesc.arraytoken,
                        argbox.getgenvar(jitstate),
                        indexbox.getgenvar(jitstate))
                    return lastfielddesc.makebox(jitstate, genvar)
                else:  # getfield
                    return argbox.op_getfield(jitstate, lastfielddesc)

            def gensetinteriorfield(jitstate, destbox, valuebox, indexboxes):
                destbox = gengetinterior_initial(jitstate, destbox, indexboxes)
                if lastoffset is None:      # setarrayitem
                    indexbox = indexboxes[-1]
                    genvar = jitstate.curbuilder.genop_setarrayitem(
                        lastfielddesc.arraytoken,
                        destbox.getgenvar(jitstate),
                        indexbox.getgenvar(jitstate),
                        valuebox.getgenvar(jitstate)
                        )
                else:  # setfield
                    destbox.op_setfield(jitstate, lastfielddesc, valuebox)

            self.perform_getinteriorfield = perform_getinteriorfield
            self.perform_setinteriorfield = perform_setinteriorfield
            self.gengetinteriorfield = gengetinteriorfield
            self.gensetinteriorfield = gensetinteriorfield

        else:
            assert isinstance(TYPE, lltype.Array)
            arrayfielddesc = ArrayFieldDesc(RGenOp, TYPE)
            perform_getinterior_all, gengetinterior_all = \
                    make_interior_getter(fielddescs)

            def perform_getinteriorarraysize(rgenop, genvar, indexes_gv):
                ptr = perform_getinterior_all(rgenop, genvar, indexes_gv)
                return rgenop.genconst(len(ptr))

            def gengetinteriorarraysize(jitstate, argbox, indexboxes):
                if argbox.is_constant():
                    # try to constant-fold
                    indexes_gv = unbox_indexes(jitstate, indexboxes)
                    if indexes_gv is not None:
                        try:
                            array = perform_getinterior_all(
                                jitstate.curbuilder.rgenop,
                                argbox.getgenvar(jitstate),
                                indexes_gv)
                        except SegfaultException:
                            pass
                        else:
                            # constant-folding: success
                            return rvalue.ll_fromvalue(jitstate, len(array))

                argbox = gengetinterior_all(jitstate, argbox, indexboxes)
                genvar = jitstate.curbuilder.genop_getarraysize(
                    arrayfielddesc.arraytoken,
                    argbox.getgenvar(jitstate))
                return rvalue.IntRedBox(genvar)

            self.perform_getinteriorarraysize = perform_getinteriorarraysize
            self.gengetinteriorarraysize = gengetinteriorarraysize

    def _freeze_(self):
        return True


def make_interior_getter(fielddescs, _cache={}):
    # returns two functions:
    #    * perform_getinterior(rgenop, gv_arg, indexes_gv)
    #    * gengetinterior(jitstate, argbox, indexboxes)
    #
    key = tuple(fielddescs)
    try:
        return _cache[key]
    except KeyError:
        unroll_fielddescs = unrolling_iterable([
            (fielddesc, isinstance(fielddesc, ArrayFieldDesc))
            for fielddesc in fielddescs])
        FIRSTPTRTYPE = fielddescs[0].PTRTYPE

        def perform_getinterior(rgenop, gv_arg, indexes_gv):
            ptr = gv_arg.revealconst(FIRSTPTRTYPE)
            if not ptr:
                raise SegfaultException    # don't constant-fold
            i = 0
            for fielddesc, is_array in unroll_fielddescs:
                if is_array:    # array substruct
                    index = indexes_gv[i].revealconst(lltype.Signed)
                    i += 1
                    if 0 <= index < len(ptr):
                        ptr = ptr[index]
                    else:
                        raise SegfaultException    # index out of bounds
                else:
                    ptr = getattr(ptr, fielddesc.fieldname)
            return ptr

        def gengetinterior(jitstate, argbox, indexboxes):
            i = 0
            for fielddesc, is_array in unroll_fielddescs:
                if is_array:    # array substruct
                    indexbox = indexboxes[i]
                    i += 1
                    genvar = jitstate.curbuilder.genop_getarraysubstruct(
                        fielddesc.arraytoken,
                        argbox.getgenvar(jitstate),
                        indexbox.getgenvar(jitstate))
                    argbox = fielddesc.makebox(jitstate, genvar)
                else:   # getsubstruct
                    argbox = argbox.op_getsubstruct(jitstate, fielddesc)
                assert isinstance(argbox, rvalue.PtrRedBox)
            return argbox

        result = perform_getinterior, gengetinterior
        _cache[key] = result
        return result

def unbox_indexes(jitstate, indexboxes):
    indexes_gv = []
    for indexbox in indexboxes:
        if not indexbox.is_constant():
            return None    # non-constant array index
        indexes_gv.append(indexbox.getgenvar(jitstate))
    return indexes_gv

# ____________________________________________________________

# XXX basic field descs for now
class FieldDesc(object):
    __metaclass__ = cachedtype
    _attrs_ = 'structdesc'
    
    allow_void = False
    virtualizable = False
    gv_default = None
    canbevirtual = False
    gcref = False
    fieldnonnull = False

    def __init__(self, RGenOp, PTRTYPE, RESTYPE):
        self.PTRTYPE = PTRTYPE
        T = None
        if isinstance(RESTYPE, lltype.ContainerType):
            T = RESTYPE
            RESTYPE = lltype.Ptr(RESTYPE)
            self.fieldnonnull = True
        elif isinstance(RESTYPE, lltype.Ptr):
            self._set_hints(PTRTYPE, RESTYPE)
            T = RESTYPE.TO
            self.gcref = T._gckind == 'gc'
            if isinstance(T, lltype.ContainerType):
                if not T._is_varsize() or hasattr(T, 'll_newlist'):
                    self.canbevirtual = True
            else:
                T = None
        elif isinstance(RESTYPE, ootype.OOType):
            self._set_hints(PTRTYPE, RESTYPE)
            self.gcref = True        # XXX: is it right?
            self.canbevirtual = True # XXX: is it right?
        self.RESTYPE = RESTYPE
        self.ptrkind = RGenOp.kindToken(PTRTYPE)
        self.kind = RGenOp.kindToken(RESTYPE)
        if self.RESTYPE is not lltype.Void:
            self.gv_default = RGenOp.constPrebuiltGlobal(self.RESTYPE._defl())
        if RESTYPE is lltype.Void and self.allow_void:
            pass   # no redboxcls at all
        else:
            if self.virtualizable:
                self.structdesc = StructTypeDesc(RGenOp, T)
            self.redboxcls = rvalue.ll_redboxcls(RESTYPE)
            
        self.immutable = deref(PTRTYPE)._hints.get('immutable', False)

    def _set_hints(self, PTRTYPE, RESTYPE):
        T = deref(RESTYPE)
        if hasattr(T, '_hints'):
            # xxx hack for simple recursive cases
            if not deref(PTRTYPE)._hints.get('virtualizable', False):
                self.virtualizable = T._hints.get('virtualizable', False)
        self.fieldnonnull = deref(PTRTYPE)._hints.get('shouldntbenull', False)

    def _freeze_(self):
        return True

    def makedefaultbox(self):
        return self.redboxcls(self.gv_default)
    
    def makebox(self, jitstate, gvar):
        if self.virtualizable:
            structbox = self.structdesc.factory()
            content = structbox.content
            assert isinstance(content, VirtualizableStruct)
            content.load_from(jitstate, gvar)
            return structbox
        box = self.redboxcls(gvar)
        if self.fieldnonnull:
            assert isinstance(box, rvalue.PtrRedBox)
            box.known_nonzero = True
        return box

    
class NamedFieldDesc(FieldDesc):

    def __init__(self, RGenOp, PTRTYPE, name):
        FIELDTYPE = fieldType(deref(PTRTYPE), name)
        FieldDesc.__init__(self, RGenOp, PTRTYPE, FIELDTYPE)
        T = deref(self.PTRTYPE)
        self.fieldname = name
        self.fieldtoken = RGenOp.fieldToken(T, name)
        def perform_getfield(rgenop, genvar):
             ptr = genvar.revealconst(PTRTYPE)
             if not ptr:
                 raise SegfaultException
             res = getattr(ptr, name)
             return rgenop.genconst(res)
        self.perform_getfield = perform_getfield
        if not isinstance(FIELDTYPE, lltype.ContainerType):
            self._define_setfield(FIELDTYPE)

    def _define_setfield(self, FIELDTYPE):
        PTRTYPE = self.PTRTYPE
        name = self.fieldname
        def perform_setfield(rgenop, genvar, gv_newvalue):
            ptr = genvar.revealconst(PTRTYPE)
            newvalue = gv_newvalue.revealconst(FIELDTYPE)
            setattr(ptr, name, newvalue)
        self.perform_setfield = perform_setfield

    def compact_repr(self): # goes in ll helper names
        return "Fld_%s_in_%s" % (self.fieldname, self.PTRTYPE._short_name())

    def generate_get(self, jitstate, genvar):
        builder = jitstate.curbuilder
        gv_item = builder.genop_getfield(self.fieldtoken, genvar)
        return self.makebox(jitstate, gv_item)

    def generate_set(self, jitstate, genvar, gv_value):
        builder = jitstate.curbuilder
        builder.genop_setfield(self.fieldtoken, genvar, gv_value)

    def generate_getsubstruct(self, jitstate, genvar):
        builder = jitstate.curbuilder
        gv_sub = builder.genop_getsubstruct(self.fieldtoken, genvar)
        return self.makebox(jitstate, gv_sub)

class StructFieldDesc(NamedFieldDesc):

    def __init__(self, RGenOp, PTRTYPE, name, index):
        NamedFieldDesc.__init__(self, RGenOp, PTRTYPE, name)
        self.fieldindex = index

class InstanceFieldDesc(NamedFieldDesc):

    def __init__(self, RGenOp, PTRTYPE, name, index):
        NamedFieldDesc.__init__(self, RGenOp, PTRTYPE, name)
        self.fieldindex = index

    def generate_get(self, jitstate, genvar):
        builder = jitstate.curbuilder
        gv_item = builder.genop_oogetfield(self.fieldtoken, genvar)
        return self.makebox(jitstate, gv_item)

    def generate_set(self, jitstate, genvar, gv_value):
        builder = jitstate.curbuilder
        builder.genop_oosetfield(self.fieldtoken, genvar, gv_value)


class ArrayFieldDesc(FieldDesc):
    allow_void = True

    def __init__(self, RGenOp, TYPE):
        assert isinstance(TYPE, lltype.Array)
        FieldDesc.__init__(self, RGenOp, lltype.Ptr(TYPE), TYPE.OF)
        self.arraytoken = RGenOp.arrayToken(TYPE)
        self.varsizealloctoken = RGenOp.varsizeAllocToken(TYPE)
        self.indexkind = RGenOp.kindToken(lltype.Signed)

        def perform_getarrayitem(rgenop, genvar, gv_index):
            array = genvar.revealconst(self.PTRTYPE)
            index = gv_index.revealconst(lltype.Signed)
            if array and 0 <= index < len(array):  # else don't constant-fold
                res = array[index]
                return rgenop.genconst(res)
            else:
                raise SegfaultException
        self.perform_getarrayitem = perform_getarrayitem

        def perform_getarraysize(rgenop, genvar):
            array = genvar.revealconst(self.PTRTYPE)
            if not array:  # don't constant-fold
                raise SegfaultException
            res = len(array)
            return rgenop.genconst(res)
        self.perform_getarraysize = perform_getarraysize

        def perform_setarrayitem(rgenop, genvar, gv_index, gv_newvalue):
            array = genvar.revealconst(self.PTRTYPE)
            index = gv_index.revealconst(lltype.Signed)
            newvalue = gv_newvalue.revealconst(TYPE.OF)
            array[index] = newvalue
        self.perform_setarrayitem = perform_setarrayitem

        if TYPE._gckind == 'gc':    # no allocate for inlined arrays
            self._define_allocate()

    def _define_allocate(self):
        TYPE = self.PTRTYPE.TO
        def allocate(rgenop, size):
            a = lltype.malloc(TYPE, size)
            return rgenop.genconst(a)
        self.allocate = allocate

# ____________________________________________________________

class FrozenVirtualStruct(FrozenContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.fz_content_boxes initialized later

    def exactmatch(self, vstruct, outgoingvarboxes, memo):
        assert isinstance(vstruct, VirtualContainer)
        contmemo = memo.containers
        if self in contmemo:
            ok = vstruct is contmemo[self]
            if not ok:
                outgoingvarboxes.append(vstruct.ownbox)
            return ok
        if vstruct in contmemo:
            assert contmemo[vstruct] is not self
            outgoingvarboxes.append(vstruct.ownbox)
            return False
        if (not isinstance(vstruct, VirtualStruct)
            or self.typedesc is not vstruct.typedesc):
            if not memo.force_merge:
                raise rvalue.DontMerge
            outgoingvarboxes.append(vstruct.ownbox)
            return False
        contmemo[self] = vstruct
        contmemo[vstruct] = self
        self_boxes = self.fz_content_boxes
        vstruct_boxes = vstruct.content_boxes
        fullmatch = True
        for i in range(len(self_boxes)):
            if not self_boxes[i].exactmatch(vstruct_boxes[i],
                                            outgoingvarboxes,
                                            memo):
                fullmatch = False
        return fullmatch

    def unfreeze(self, incomingvarboxes, memo):
        contmemo = memo.containers
        if self in contmemo:
            return contmemo[self]
        typedesc = self.typedesc
        ownbox = typedesc.factory()
        contmemo[self] = ownbox
        vstruct = ownbox.content
        assert isinstance(vstruct, VirtualStruct)
        self_boxes = self.fz_content_boxes
        for i in range(len(self_boxes)):
            fz_box = self_boxes[i]
            vstruct.content_boxes[i] = fz_box.unfreeze(incomingvarboxes,
                                                       memo)
        return ownbox

class VirtualStruct(VirtualContainer):
    _attrs_ = "typedesc content_boxes".split()

    allowed_in_virtualizable = True
    
    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.content_boxes = ... set in factory()
        #self.ownbox = ... set in factory()

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.content_boxes:
                box.enter_block(incoming, memo)

    def setforced(self, gv_forced):
        self.content_boxes = None
        self.ownbox.setgenvar_hint(gv_forced, known_nonzero=True)
        self.ownbox.content = None
        
    def force_runtime_container(self, jitstate):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        boxes = self.content_boxes
        self.content_boxes = None
        if typedesc.materialize is not None:
            for box in boxes:
                if box is None or not box.is_constant():
                    break
            else:
                gv = typedesc.materialize(builder.rgenop, boxes)
                self.ownbox.setgenvar_hint(gv, known_nonzero=True)
                self.ownbox.content = None
                return
        debug_print(lltype.Void, "FORCE CONTAINER: "+ typedesc.TYPE._name)
        #debug_pdb(lltype.Void)
        genvar = jitstate.ts.genop_malloc_fixedsize(builder, typedesc.alloctoken)
        # force the box pointing to this VirtualStruct
        self.setforced(genvar)
        fielddescs = typedesc.fielddescs
        for i in range(len(fielddescs)):
            fielddesc = fielddescs[i]
            box = boxes[i]
            fielddesc.generate_set(jitstate, genvar, box.getgenvar(jitstate))

    def freeze(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = FrozenVirtualStruct(self.typedesc)
        frozens = [box.freeze(memo) for box in self.content_boxes]
        result.fz_content_boxes = frozens
        return result

    def copy(self, memo):
        typedesc = self.typedesc
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = typedesc.VirtualStructCls(typedesc)
        result.content_boxes = [box.copy(memo)
                                for box in self.content_boxes]
        result.ownbox = self.ownbox.copy(memo)
        return result

    def replace(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        contmemo[self] = None
        content_boxes = self.content_boxes
        for i in range(len(content_boxes)):
            content_boxes[i] = content_boxes[i].replace(memo)
        self.ownbox = self.ownbox.replace(memo)

    def op_getfield(self, jitstate, fielddesc):
        return self.content_boxes[fielddesc.fieldindex]

    def op_setfield(self, jitstate, fielddesc, valuebox):
        self.content_boxes[fielddesc.fieldindex] = valuebox

    def op_getsubstruct(self, jitstate, fielddesc):
        return self.ownbox

    def make_rti(self, jitstate, memo):
        try:
            return memo.containers[self]
        except KeyError:
            pass
        typedesc = self.typedesc
        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        rgenop = jitstate.curbuilder.rgenop
        vrti = rvirtualizable.VirtualRTI(rgenop, bitmask)
        vrti.devirtualize = typedesc.devirtualize
        memo.containers[self] = vrti

        builder = jitstate.curbuilder
        place = builder.alloc_frame_place(typedesc.ptrkind)
        vrti.forced_place = place
        forced_box = rvalue.PtrRedBox()
        memo.forced_boxes.append((forced_box, place))

        vars_gv = memo.framevars_gv
        varindexes = vrti.varindexes
        vrtis = vrti.vrtis
        j = -1
        for box in self.content_boxes:
            if box.genvar:
                varindexes.append(memo.frameindex)
                memo.frameindex += 1
                vars_gv.append(box.genvar)
            else:
                varindexes.append(j)
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable                
                vrtis.append(content.make_rti(jitstate, memo))
                j -= 1

        self.content_boxes.append(forced_box)
        return vrti

    def reshape(self, jitstate, shapemask, memo):
        if self in memo.containers:
            return
        typedesc = self.typedesc
        builder = jitstate.curbuilder        
        memo.containers[self] = None
        bitmask = 1<<memo.bitcount
        memo.bitcount += 1

        boxes = self.content_boxes
        outside_box = boxes.pop()
        if bitmask&shapemask:
            gv_forced = outside_box.genvar
            memo.forced.append((self, gv_forced))
            
        for box in boxes:
            if not box.genvar:
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.reshape(jitstate, shapemask, memo)

    def store_back_gv_reshaped(self, shapemask, memo):
        if self in memo.containers:
            return
        typedesc = self.typedesc
        memo.containers[self] = None
        bitmask = 1<<memo.bitcount
        memo.bitcount += 1

        boxes = self.content_boxes
        outside_box = boxes[-1]
        if bitmask&shapemask:
            gv_forced = memo.box_gv_reader(outside_box)
            memo.forced_containers_gv[self] = gv_forced
            
        for box in boxes:
            if not box.genvar:
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.store_back_gv_reshaped(shapemask, memo)

    def allocate_gv_container(self, rgenop, need_reshaping=False):
        typedesc = self.typedesc
        # this should not be used for already-allocated virtualizables
        assert (not isinstance(self, VirtualizableStruct)
                or self.content_boxes[-1].genvar is typedesc.gv_null)
        return typedesc.allocate(rgenop)

    def populate_gv_container(self, rgenop, gv_structptr, box_gv_reader):
        # this should not be used for already-allocated virtualizables
        self.typedesc.populate(self.content_boxes, gv_structptr, box_gv_reader)

class VirtualizableStruct(VirtualStruct):
    
    def force_runtime_container(self, jitstate):
        assert 0

    def getgenvar(self, jitstate):
        typedesc = self.typedesc
        gv_outside = self.content_boxes[-1].genvar
        if gv_outside is typedesc.gv_null:
            assert isinstance(typedesc, VirtualizableStructTypeDesc)
            builder = jitstate.curbuilder
            gv_outside = builder.genop_malloc_fixedsize(typedesc.alloctoken)
            outsidebox = rvalue.PtrRedBox(gv_outside,
                                          known_nonzero = True)
            self.content_boxes[-1] = outsidebox
            jitstate.add_virtualizable(self.ownbox)
            #access_token = typedesc.access_desc.fieldtoken            
            #gv_access_null = typedesc.access_desc.gv_default
            #builder.genop_setfield(access_token, gv_outside, gv_access_null)
            # write all non-redirected fields
            boxes = self.content_boxes
            fielddescs = typedesc.fielddescs
            redirected = typedesc.redirected
            for i in range(len(fielddescs)):
                if i not in redirected:
                    fielddesc = fielddescs[i]
                    box = boxes[i]
                    fielddesc.generate_set(jitstate, gv_outside,
                                           box.getgenvar(jitstate))
        return gv_outside

    def store_back(self, jitstate):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        boxes = self.content_boxes
        gv_outside = boxes[-1].genvar
        for fielddesc, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            fielddesc.generate_set(jitstate, gv_outside,
                                   box.getgenvar(jitstate))

    def load_from(self, jitstate, gv_outside):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        assert self.content_boxes[-1].genvar is typedesc.gv_null
        boxes = self.content_boxes
        boxes[-1] = rvalue.PtrRedBox(gv_outside,
                                     known_nonzero=True)
        builder = jitstate.curbuilder
        builder.genop_call(typedesc.access_is_null_token,
                           typedesc.get_gv_access_is_null(builder),
                           [gv_outside])
        for fielddesc, i in typedesc.redirected_fielddescs:
            boxes[i] = fielddesc.generate_get(jitstate, gv_outside)
        jitstate.add_virtualizable(self.ownbox)

    def make_rti(self, jitstate, memo):
        typedesc = self.typedesc
        outsidebox = self.content_boxes[-1]
        gv_outside = outsidebox.genvar
        if gv_outside is typedesc.gv_null:
            return None
        try:
            return memo.containers[self]
        except KeyError:
            pass
        assert isinstance(typedesc, VirtualizableStructTypeDesc)        
        rgenop = jitstate.curbuilder.rgenop
        vable_rti = rvirtualizable.VirtualizableRTI(rgenop, 0)
        vable_rti.touch_update = typedesc.touch_update
        vable_rti.shape_place = jitstate.shape_place
        memo.containers[self] = vable_rti
        
        vars_gv = memo.framevars_gv
        varindexes = vable_rti.varindexes
        vrtis = vable_rti.vrtis
        boxes = self.content_boxes
        j = -1
        for _, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            if box.genvar:
                varindexes.append(memo.frameindex)
                memo.frameindex += 1
                vars_gv.append(box.genvar)
            else:
                varindexes.append(j)
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                vrtis.append(content.make_rti(jitstate, memo))
                j -= 1

        nvirtual = -j-1
        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        memo.bitcount += nvirtual
        vable_rti.bitmask = bitmask
        return vable_rti

    def prepare_for_residual_call(self, jitstate, gv_base, vable_rti):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)        
        builder = jitstate.curbuilder
        gv_outside = self.content_boxes[-1].genvar
        base_desc = typedesc.base_desc
        base_token = base_desc.fieldtoken
        builder.genop_setfield(base_token, gv_outside, gv_base)
        if we_are_translated():
            vable_rti_ptr = cast_instance_to_base_ptr(vable_rti)
        else:
            vable_rti_ptr = vable_rti

        gv_vable_rti = builder.rgenop.genconst(vable_rti_ptr)
        rti_token = typedesc.rti_desc.fieldtoken
        builder.genop_setfield(rti_token, gv_outside, gv_vable_rti)
        access_token = typedesc.access_desc.fieldtoken
        builder.genop_setfield(access_token, gv_outside,
                               typedesc.get_gv_access(builder))

    def check_forced_after_residual_call(self, jitstate):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        gv_outside = self.content_boxes[-1].genvar
        if gv_outside is typedesc.gv_null:
            return
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        access_token = typedesc.access_desc.fieldtoken            
        gv_access_null = typedesc.access_desc.gv_default
        builder.genop_setfield(access_token, gv_outside, gv_access_null)


    def reshape(self, jitstate, shapemask, memo):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        gv_outside = self.content_boxes[-1].genvar
        if gv_outside is typedesc.gv_null:
            return
        if self in memo.containers:
            return
        memo.containers[self] = None
        assert isinstance(typedesc, VirtualizableStructTypeDesc)

        boxes = self.content_boxes
        nvirtual = 0
        for _, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            if not box.genvar:
                nvirtual += 1
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.reshape(jitstate, shapemask, memo)

        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        memo.bitcount += nvirtual
        if shapemask&bitmask:   # touched by anything during the residual call?
            vmask = bitmask
            for fielddesc, i in typedesc.redirected_fielddescs:
                box = boxes[i]
                if not box.genvar:
                    vmask = vmask<<1
                    if not (shapemask&vmask):
                        continue
                boxes[i] = fielddesc.generate_get(jitstate, gv_outside)

    def store_back_gv(self, rgenop, box_gv_reader):
        # store back the fields' value from the machine code stack into
        # the heap-based virtualizable object
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        outsidebox = self.content_boxes[-1]
        if outsidebox.genvar is typedesc.gv_null:
            return None
        gv_outside = box_gv_reader(outsidebox)
        for fielddesc, i in typedesc.redirected_fielddescs:
            box = self.content_boxes[i]
            gv_value = box_gv_reader(box)
            fielddesc.perform_setfield(rgenop, gv_outside, gv_value)
        return gv_outside

    def store_back_gv_reshaped(self, shapemask, memo):
        # store back the fields' value from the machine code stack into
        # the heap-based virtualizable objects.  Advanced case: this
        # occurs just after a residual call, where 'self' is in a state
        # that requires the equivalent of a reshape().  In other words
        # we cannot just copy all fields from the stack to the heap
        # because the heap virtualizable might already contain some
        # values that were written there during the residual call.  We
        # have to decode the shapemask to know what is where...
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        boxes = self.content_boxes
        outsidebox = boxes[-1]
        if outsidebox.genvar is typedesc.gv_null:
            return
        if self in memo.containers:
            return
        memo.containers[self] = None

        gv_outside = memo.box_gv_reader(outsidebox)
        memo.forced_containers_gv[self] = gv_outside

        nvirtual = 0
        for _, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            if not box.genvar:
                nvirtual += 1
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.store_back_gv_reshaped(shapemask, memo)

        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        memo.bitcount += nvirtual
        touched = shapemask&bitmask
        # if 'touched' is set, then the virtualizable on the heap contains
        # the correct values for all fields except possibly the ones that
        # point, or used to point, to virtual container
        vmask = bitmask
        for fielddesc, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            if not box.genvar:
                vmask = vmask<<1
                if shapemask&vmask:
                    # this field used to point to a virtual container, but
                    # a new value was already stored in the virtualizable
                    continue
                else:
                    # this field still points to a virtual container,
                    # which needs to be materialized and stored back
                    pass
            else:
                if touched:
                    # this is a regular field that was already stored
                    # in the virtualizable when it was first touched
                    continue
                else:
                    # a regular field to store back
                    pass
            # the actual copying is done later, to avoid strange interactions
            # between the current recursive visit and a call to box_gv_reader()
            # on a virtual structure; indeed, both update the containers_gv
            # dictionary of the fallback interpreter
            memo.copyfields.append((gv_outside, fielddesc, box))

    def op_getfield(self, jitstate, fielddesc):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        gv_outside = self.content_boxes[-1].genvar
        fieldindex = fielddesc.fieldindex
        if (gv_outside is typedesc.gv_null or
            fieldindex in typedesc.redirected):
            return self.content_boxes[fieldindex]
        else:
            gv_ptr = self.getgenvar(jitstate)
            box = fielddesc.generate_get(jitstate, gv_ptr)
            return box
        
    def op_setfield(self, jitstate, fielddesc, valuebox):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        fieldindex = fielddesc.fieldindex
        gv_outside = self.content_boxes[-1].genvar
        if (gv_outside is typedesc.gv_null or
            fieldindex in typedesc.redirected):
            self.content_boxes[fielddesc.fieldindex] = valuebox
        else:
            gv_ptr = self.getgenvar(jitstate)
            fielddesc.generate_set(jitstate, gv_ptr,
                                   valuebox.getgenvar(jitstate))

    def op_ptreq(self, jitstate, otherbox, reverse):
        if self is otherbox.content:
            answer = True
        else:
            gv_outside = self.content_boxes[-1].genvar
            if gv_outside is self.typedesc.gv_null:
                answer = False
            else:
                return None   # fall-back
        return rvalue.ll_fromvalue(jitstate, answer ^ reverse)


# patching VirtualStructCls
StructTypeDesc.VirtualStructCls = VirtualStruct
InstanceTypeDesc.VirtualStructCls = VirtualStruct
VirtualizableStructTypeDesc.VirtualStructCls = VirtualizableStruct


# ____________________________________________________________

class FrozenPartialDataStruct(AbstractContainer):

    def __init__(self):
        self.fz_data = []

    def getfzbox(self, searchindex):
        for index, fzbox in self.fz_data:
            if index == searchindex:
                return fzbox
        else:
            return None

    def match(self, box, partialdatamatch):
        content = box.content
        if not isinstance(content, PartialDataStruct):
            return False

        cankeep = {}
        for index, subbox in content.data:
            selfbox = self.getfzbox(index)
            if selfbox is not None and selfbox.is_constant_equal(subbox):
                cankeep[index] = None
        fullmatch = len(cankeep) == len(self.fz_data)
        try:
            prevkeep = partialdatamatch[box]
        except KeyError:
            partialdatamatch[box] = cankeep
        else:
            if prevkeep is not None:
                d = {}
                for index in prevkeep:
                    if index in cankeep:
                        d[index] = None
                partialdatamatch[box] = d
        return fullmatch


class PartialDataStruct(AbstractContainer):

    def __init__(self):
        self.data = []

    def op_getfield(self, jitstate, fielddesc):
        searchindex = fielddesc.fieldindex
        for index, box in self.data:
            if index == searchindex:
                return box
        else:
            return None

    def op_ptreq(self, jitstate, otherbox, reverse):
        return None    # XXX for now

    def remember_field(self, fielddesc, box):
        searchindex = fielddesc.fieldindex
        for i in range(len(self.data)):
            if self.data[i][0] == searchindex:
                self.data[i] = searchindex, box
                return
        else:
            self.data.append((searchindex, box))

    def partialfreeze(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = FrozenPartialDataStruct()
        for index, box in self.data:
            if box.is_constant():
                frozenbox = box.freeze(memo)
                result.fz_data.append((index, frozenbox))
        if len(result.fz_data) == 0:
            return None
        else:
            return result

    def copy(self, memo):
        result = PartialDataStruct()
        for index, box in self.data:
            result.data.append((index, box.copy(memo)))
        return result

    def replace(self, memo):
        for i in range(len(self.data)):
            index, box = self.data[i]
            box = box.replace(memo)
            self.data[i] = index, box

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for index, box in self.data:
                box.enter_block(incoming, memo)

    def cleanup_partial_data(self, keep):
        if keep is None:
            return None
        j = 0
        data = self.data
        for i in range(len(data)):
            item = data[i]
            if item[0] in keep:
                data[j] = item
                j += 1
        if j == 0:
            return None
        del data[j:]
        return self



StructTypeDesc.StructFieldDesc = StructFieldDesc
InstanceTypeDesc.StructFieldDesc = InstanceFieldDesc
