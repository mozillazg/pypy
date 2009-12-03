from pypy.rpython.rmodel import inputconst, log
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass


def replace_force_virtual_with_call(graphs, funcptr):
    # similar to rvirtualizable2.replace_force_virtualizable_with_call().
    # funcptr should be an ll function pointer with a signature
    # OBJECTPTR -> OBJECTPTR.
    c_funcptr = inputconst(lltype.typeOf(funcptr), funcptr)
    count = 0
    for graph in graphs:
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'jit_force_virtual':
                    op.opname = 'direct_call'
                    op.args = [c_funcptr, op.args[0]]
                    count += 1
    log("replaced %d 'jit_force_virtual' with %r" % (count, funcptr))

# ____________________________________________________________


# we make the low-level type of an RPython class directly
JIT_VIRTUAL_REF = lltype.GcStruct('JitVirtualRef',
                                  ('super', rclass.OBJECT),
                                  ('force_token', llmemory.Address),
                                  ('forced', rclass.OBJECTPTR))
jit_virtual_ref_vtable = lltype.malloc(rclass.OBJECT_VTABLE, zero=True,
                                       flavor='raw')

class ForceTokenMem(object):
    def __init__(self):
        self.allocated = lltype.malloc(rffi.CArray(lltype.Signed), 1,
                                       flavor='raw')
        self.allocated[0] = 0

    def __del__(self):
        lltype.free(self.allocated, flavor='raw')

def get_force_token(metainterp):
    if not metainterp._force_token_mem:
        metainterp._force_token_mem = ForceTokenMem()
    return llmemory.cast_ptr_to_adr(metainterp._force_token_mem.allocated)

def was_forced(metainterp):
    if not metainterp._force_token_mem:
        return False
    return metainterp._force_token_mem.allocated[0] == -1

def virtual_ref_during_tracing(metainterp, real_object):
    vref = lltype.malloc(JIT_VIRTUAL_REF)
    p = lltype.cast_pointer(rclass.OBJECTPTR, vref)
    p.typeptr = jit_virtual_ref_vtable
    vref.force_token = get_force_token(metainterp)
    vref.forced = lltype.cast_opaque_ptr(rclass.OBJECTPTR, real_object)
    assert vref.forced
    return lltype.cast_opaque_ptr(llmemory.GCREF, vref)

# ____________________________________________________________

def force_virtual_if_necessary(inst):
    if not inst or inst.typeptr != jit_virtual_ref_vtable:
        return inst    # common, fast case
    return force_virtual(inst)

def force_virtual(inst):
    vref = lltype.cast_pointer(lltype.Ptr(JIT_VIRTUAL_REF), inst)
    if vref.force_token:
        if not vref.forced:
            xxxx
        vref.force_token.signed[0] = -1
        vref.force_token = llmemory.NULL
    return vref.forced
force_virtual._dont_inline_ = True
