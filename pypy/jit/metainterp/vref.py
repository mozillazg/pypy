from pypy.rpython.rmodel import inputconst, log
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass


def replace_force_virtual_with_call(make_helper_func, graphs):
    # similar to rvirtualizable2.replace_force_virtualizable_with_call().
    c_funcptr = None
    count = 0
    for graph in graphs:
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname == 'jit_force_virtual':
                    # first compute c_funcptr, but only if there is any
                    # 'jit_force_virtual' around
                    if c_funcptr is None:
                        FUNC = lltype.FuncType([rclass.OBJECTPTR],
                                               rclass.OBJECTPTR)
                        funcptr = make_helper_func(
                            lltype.Ptr(FUNC),
                            force_virtual_if_necessary)
                        c_funcptr = inputconst(lltype.typeOf(funcptr), funcptr)
                    #
                    op.opname = 'direct_call'
                    op.args = [c_funcptr, op.args[0]]
                    count += 1
    if c_funcptr is not None:
        log("replaced %d 'jit_force_virtual' with %r" % (count, funcptr))

# ____________________________________________________________


# we make the low-level type of an RPython class directly
JIT_VIRTUAL_REF = lltype.GcStruct('JitVirtualRef',
                                  ('super', rclass.OBJECT),
                                  ('virtual_token', lltype.Signed),
                                  ('forced', rclass.OBJECTPTR))
jit_virtual_ref_vtable = lltype.malloc(rclass.OBJECT_VTABLE, zero=True,
                                       flavor='raw')

# The 'virtual_token' field has the same meaning as the 'vable_token' field
# of a virtualizable.  It is equal to:
#   * -1 (TOKEN_TRACING) when tracing;
#   * addr in the CPU stack (set by FORCE_TOKEN) when running the assembler;
#   * 0 (TOKEN_NONE) after the virtual is forced, if it is forced at all.
TOKEN_NONE    = 0
TOKEN_TRACING = -1

def virtual_ref_during_tracing(real_object):
    assert real_object
    vref = lltype.malloc(JIT_VIRTUAL_REF)
    p = lltype.cast_pointer(rclass.OBJECTPTR, vref)
    p.typeptr = jit_virtual_ref_vtable
    vref.virtual_token = TOKEN_TRACING
    vref.forced = lltype.cast_opaque_ptr(rclass.OBJECTPTR, real_object)
    return lltype.cast_opaque_ptr(llmemory.GCREF, vref)

def was_forced(gcref):
    vref = lltype.cast_opaque_ptr(lltype.Ptr(JIT_VIRTUAL_REF), gcref)
    return vref.virtual_token != TOKEN_TRACING

# ____________________________________________________________

def force_virtual_if_necessary(inst):
    if not inst or inst.typeptr != jit_virtual_ref_vtable:
        return inst    # common, fast case
    return force_virtual(inst)

def force_virtual(inst):
    vref = lltype.cast_pointer(lltype.Ptr(JIT_VIRTUAL_REF), inst)
    if not vref.forced:
        xxxx
    vref.virtual_token = TOKEN_NONE
    return vref.forced
force_virtual._dont_inline_ = True
