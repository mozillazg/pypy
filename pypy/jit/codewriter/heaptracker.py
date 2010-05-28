from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rlib.objectmodel import we_are_translated


def get_vtable_for_gcstruct(cpu, GCSTRUCT):
    # xxx hack: from a GcStruct representing an instance's
    # lowleveltype, return the corresponding vtable pointer.
    # Returns None if the GcStruct does not belong to an instance.
    assert isinstance(GCSTRUCT, lltype.GcStruct)
    HEAD = GCSTRUCT
    while not HEAD._hints.get('typeptr'):
        _, HEAD = HEAD._first_struct()
        if HEAD is None:
            return None
    setup_cache_gcstruct2vtable(cpu)
    return cpu._cache_gcstruct2vtable[GCSTRUCT]

def setup_cache_gcstruct2vtable(cpu):
    if not hasattr(cpu, '_cache_gcstruct2vtable'):
        cache = {}
        cache.update(testing_gcstruct2vtable)
        for rinstance in cpu.rtyper.instance_reprs.values():
            cache[rinstance.lowleveltype.TO] = rinstance.rclass.getvtable()
        cpu._cache_gcstruct2vtable = cache

def set_testing_vtable_for_gcstruct(GCSTRUCT, vtable, name):
    # only for tests that need to register the vtable of their malloc'ed
    # structures in case they are GcStruct inheriting from OBJECT.
    namez = name + '\x00'
    vtable.name = lltype.malloc(rclass.OBJECT_VTABLE.name.TO, len(namez),
                                immortal=True)
    for i in range(len(namez)):
        vtable.name[i] = namez[i]
    testing_gcstruct2vtable[GCSTRUCT] = vtable

testing_gcstruct2vtable = {}

# ____________________________________________________________

VTABLETYPE = rclass.CLASSTYPE

def register_known_gctype(cpu, vtable, STRUCT):
    # register the correspondance 'vtable' <-> 'STRUCT' in the cpu
    sizedescr = cpu.sizeof(STRUCT)
    if hasattr(sizedescr, '_corresponding_vtable'):
        assert sizedescr._corresponding_vtable == vtable
    else:
        assert lltype.typeOf(vtable) == VTABLETYPE
        if not hasattr(cpu, '_all_size_descrs_with_vtable'):
            cpu._all_size_descrs_with_vtable = []
            cpu._vtable_to_descr_dict = None
        cpu._all_size_descrs_with_vtable.append(sizedescr)
        sizedescr._corresponding_vtable = vtable

def finish_registering(cpu):
    # annotation hack for small examples which have no vtable at all
    if not hasattr(cpu, '_all_size_descrs_with_vtable'):
        STRUCT = lltype.GcStruct('empty')
        vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        register_known_gctype(cpu, vtable, STRUCT)

def vtable2descr(cpu, vtable):
    assert lltype.typeOf(vtable) is lltype.Signed
    if we_are_translated():
        # Build the dict {vtable: sizedescr} at runtime.
        # This is necessary because the 'vtables' are just pointers to
        # static data, so they can't be used as keys in prebuilt dicts.
        d = cpu._vtable_to_descr_dict
        if d is None:
            d = cpu._vtable_to_descr_dict = {}
            for descr in cpu._all_size_descrs_with_vtable:
                key = descr._corresponding_vtable
                key = llmemory.cast_ptr_to_adr(key)
                key = llmemory.cast_adr_to_int(key)
                d[key] = descr
        return d[vtable]
    else:
        vtable = llmemory.cast_int_to_adr(vtable)
        vtable = llmemory.cast_adr_to_ptr(vtable, VTABLETYPE)
        for descr in cpu._all_size_descrs_with_vtable:
            if descr._corresponding_vtable == vtable:
                return descr
        raise KeyError(vtable)

def descr2vtable(cpu, descr):
    from pypy.jit.metainterp import history
    assert isinstance(descr, history.AbstractDescr)
    vtable = descr._corresponding_vtable
    vtable = llmemory.cast_ptr_to_adr(vtable)
    vtable = llmemory.cast_adr_to_int(vtable)
    return vtable
